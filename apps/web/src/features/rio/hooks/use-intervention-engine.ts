/**
 * useInterventionEngine - Rio's observation and intervention logic
 *
 * Triggers interventions based on:
 * - Long work sessions (45/90/120 min)
 * - Idle time (10/30 min)
 * - Late-night work (12am-5am)
 * - Mission deadlines (<3 hours)
 * - Streak risk (>20 hours since last interaction)
 * - Pattern anomalies (productive hours)
 */

import { useEffect, useRef } from 'react'
import { useActivityMonitor } from '@/shared/hooks/use-activity-monitor'
import { useInterventionStore, InterventionType } from '@/features/rio/store'
import { useEmotionalStore } from '@/features/emotional/store'
import { useMissionStore } from '@/features/mission/store'
import { generateRioResponse, type ResponseContext } from '@/features/rio/lib/rio-response-generator'

export function useInterventionEngine() {
  const activityData = useActivityMonitor()
  const { triggerIntervention, preferences } = useInterventionStore()
  const { mood, affinity, relationshipTier } = useEmotionalStore()
  const { missions } = useMissionStore()

  const lastBreakReminderRef = useRef(0)
  const lastIdleCheckRef = useRef(0)
  const sessionStartRef = useRef(Date.now())

  // Generate LLM-powered intervention message
  const generateMessage = async (situationType: ResponseContext['situationType'], additionalInfo?: any) => {
    const context: ResponseContext = {
      mood,
      energy: 1.0,
      affinity,
      relationshipTier,
      streakDays: 0,
      sessionDuration: activityData.sessionDuration,
      idleTime: activityData.idleTime,
      isLateNight: activityData.isLateNight,
      isWeekend: activityData.isWeekend,
      eventCount: activityData.eventCount,
      situationType,
      additionalInfo,
    }

    const response = await generateRioResponse(context)
    return response.message
  }

  useEffect(() => {
    if (preferences.breakFrequency === 0) return

    const { sessionDuration, isIdle } = activityData
    if (isIdle) return

    const now = Date.now()
    const timeSinceLastReminder = now - lastBreakReminderRef.current
    if (timeSinceLastReminder < 10 * 60 * 1000) return

    const sessionMinutes = sessionDuration / (60 * 1000)

    if (sessionMinutes >= 45 && sessionMinutes < 46) {
      lastBreakReminderRef.current = now
      generateMessage('intervention_45min').then((message) => {
        triggerIntervention({ type: 'toast', message, triggerReason: 'long_session_45' })
      })
    } else if (sessionMinutes >= 90 && sessionMinutes < 91) {
      lastBreakReminderRef.current = now
      generateMessage('intervention_90min').then((message) => {
        triggerIntervention({
          type: 'modal', message, triggerReason: 'long_session_90',
          actions: [
            { label: 'Take a Break', action: 'accept', affinityChange: 2 },
            { label: 'Remind Me in 15 min', action: 'remind' },
            { label: 'Keep Working', action: 'dismiss', affinityChange: -1 },
          ],
        })
      })
    } else if (sessionMinutes >= 120 && sessionMinutes < 121) {
      if (!preferences.allowBlocking) return
      lastBreakReminderRef.current = now
      generateMessage('intervention_120min').then((message) => {
        triggerIntervention({
          type: 'blocking', message, triggerReason: 'long_session_120', countdown: 60,
          actions: [
            { label: 'Start Break', action: 'accept', affinityChange: 5 },
            { label: 'Override (will decrease affinity)', action: 'override', affinityChange: -10 },
          ],
        })
      })
    }
  }, [
    activityData.sessionDuration, activityData.isIdle,
    preferences.breakFrequency, preferences.allowBlocking,
    triggerIntervention, mood, relationshipTier,
  ])

  useEffect(() => {
    const { isIdle, idleTime } = activityData
    const now = Date.now()

    if (!isIdle) { lastIdleCheckRef.current = 0; return }

    const timeSinceLastCheck = now - lastIdleCheckRef.current
    if (timeSinceLastCheck < 5 * 60 * 1000) return

    lastIdleCheckRef.current = now
    const idleMinutes = Math.floor(idleTime / (60 * 1000))

    if (idleMinutes >= 10 && idleMinutes < 15) {
      generateMessage('idle_check').then((message) => {
        triggerIntervention({ type: 'toast', message, triggerReason: 'idle_10' })
      })
    } else if (idleMinutes >= 30) {
      generateMessage('idle_check', { idle_minutes: idleMinutes }).then((message) => {
        triggerIntervention({
          type: 'modal', message, triggerReason: 'idle_30',
          actions: [
            { label: "I'm Here", action: 'dismiss' },
            { label: 'Start New Chat', action: 'accept' },
          ],
        })
      })
    }
  }, [activityData.isIdle, activityData.idleTime, triggerIntervention, mood, relationshipTier])

  // 3. Late-night work detection
  useEffect(() => {
    const { isLateNight, sessionDuration, isIdle } = activityData
    if (!isLateNight || isIdle || !preferences.workHourLimits) return

    const sessionMinutes = sessionDuration / (60 * 1000)
    if (sessionMinutes >= 15 && sessionMinutes < 16) {
      generateMessage('late_night_warning').then((message) => {
        triggerIntervention({
          type: 'modal', message, triggerReason: 'late_night_work',
          actions: [
            { label: "I'll Sleep Soon", action: 'dismiss' },
            { label: 'Just a Bit Longer', action: 'dismiss', affinityChange: -1 },
          ],
        })
      })
    }
  }, [
    activityData.isLateNight, activityData.sessionDuration, activityData.isIdle,
    preferences.workHourLimits, triggerIntervention, mood, relationshipTier,
  ])

  useEffect(() => {
    const urgentMissions = missions.filter((m) => {
      if (m.status !== 'active' || !m.deadline) return false
      const deadline = new Date(m.deadline)
      const hoursUntil = (deadline.getTime() - Date.now()) / (1000 * 60 * 60)
      return hoursUntil > 0 && hoursUntil <= 3
    })

    if (urgentMissions.length > 0 && !activityData.isIdle) {
      const mission = urgentMissions[0]
      const deadline = new Date(mission.deadline!)
      const hoursUntil = Math.floor((deadline.getTime() - Date.now()) / (1000 * 60 * 60))

      generateMessage('deadline_pressure', {
        mission_title: mission.title,
        hours_until_deadline: hoursUntil,
      }).then((message) => {
        triggerIntervention({ type: 'toast', message, triggerReason: `deadline_pressure_${mission.id}` })
      })
    }
  }, [missions, activityData.isIdle, triggerIntervention])

  // 5. Re-engagement after long absence
  useEffect(() => {
    if (typeof window === 'undefined') return
    const lastInteraction = localStorage.getItem('last-interaction-time')
    if (!lastInteraction) return

    const hoursSinceLastInteraction = (Date.now() - parseInt(lastInteraction)) / (1000 * 60 * 60)
    if (hoursSinceLastInteraction >= 24) {
      generateMessage('re_engagement', {
        hours_since_last_interaction: Math.floor(hoursSinceLastInteraction),
      }).then((message) => {
        triggerIntervention({
          type: 're-engagement', message, triggerReason: 're_engagement',
          actions: [
            { label: "What's New?", action: 'accept' },
            { label: 'Resume Last Chat', action: 'accept' },
            { label: 'View Missions', action: 'accept' },
          ],
        })
      })
      localStorage.setItem('last-interaction-time', Date.now().toString())
    }
  }, [triggerIntervention, mood, relationshipTier])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const updateLastInteraction = () => {
      localStorage.setItem('last-interaction-time', Date.now().toString())
    }
    window.addEventListener('click', updateLastInteraction)
    window.addEventListener('keydown', updateLastInteraction)
    return () => {
      window.removeEventListener('click', updateLastInteraction)
      window.removeEventListener('keydown', updateLastInteraction)
    }
  }, [])
}
