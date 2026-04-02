/**
 * useRioObservation - Context-aware Rio observations
 */

import { useState, useEffect, useRef } from 'react'
import { useMissionStore } from '@/features/mission/store'

const IDLE_THRESHOLD = 10 * 60 * 1000
const LONG_SESSION_THRESHOLD_1 = 45 * 60 * 1000
const LONG_SESSION_THRESHOLD_2 = 90 * 60 * 1000
const LONG_SESSION_THRESHOLD_3 = 120 * 60 * 1000

export interface RioObservation {
  message: string
  type: 'idle' | 'mission_progress' | 'long_session' | 'resume' | 'late_night' | 'deadline_pressure' | null
}

export function useRioObservation() {
  const [observation, setObservation] = useState<RioObservation | null>(null)
  const [lastActivityTime, setLastActivityTime] = useState(Date.now())
  const sessionStartRef = useRef(Date.now())
  const missions = useMissionStore((state) => state.missions)
  const prevMissionsRef = useRef(missions)

  useEffect(() => {
    const updateActivity = () => {
      setLastActivityTime(Date.now())
      setObservation((prev) => (prev?.type === 'idle' ? null : prev))
    }
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
    events.forEach((event) => window.addEventListener(event, updateActivity))
    return () => { events.forEach((event) => window.removeEventListener(event, updateActivity)) }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const timeSinceActivity = now - lastActivityTime
      if (timeSinceActivity > IDLE_THRESHOLD) {
        setObservation({ message: "You've been quiet for a while. Stuck on something?", type: 'idle' })
      }
      const sessionDuration = now - sessionStartRef.current
      if (sessionDuration > LONG_SESSION_THRESHOLD_3) {
        setObservation({ message: "Critical: 2 hours without a break. This is unhealthy. Please rest immediately.", type: 'long_session' })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_3 / 2)
      } else if (sessionDuration > LONG_SESSION_THRESHOLD_2) {
        setObservation({ message: "Long session detected (90+ minutes). Time for a proper break.", type: 'long_session' })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_2 / 2)
      } else if (sessionDuration > LONG_SESSION_THRESHOLD_1) {
        setObservation({ message: "You've been focused for 45 minutes. Great work! Consider a quick break.", type: 'long_session' })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_1 / 2)
      }
      const hour = new Date().getHours()
      if (hour >= 0 && hour < 5 && sessionDuration > 15 * 60 * 1000) {
        setObservation({ message: "It's very late (past midnight). Working now can harm your health. Please sleep.", type: 'late_night' })
      }
    }, 60000)
    return () => clearInterval(interval)
  }, [lastActivityTime])

  useEffect(() => {
    const prevMissions = prevMissionsRef.current
    const activeMissions = missions.filter((m) => m.status === 'active')
    const newlyCompleted = prevMissions.find((pm) => {
      const current = missions.find((m) => m.id === pm.id)
      return pm.status === 'active' && current && current.status === 'completed'
    })
    if (newlyCompleted) {
      const remaining = activeMissions.length
      if (remaining > 0) {
        setObservation({ message: `Good progress on "${newlyCompleted.title}". ${remaining} active mission${remaining !== 1 ? 's' : ''} remaining.`, type: 'mission_progress' })
      } else {
        setObservation({ message: `Mission complete! All tasks cleared. Time to relax?`, type: 'mission_progress' })
      }
      setTimeout(() => { setObservation((prev) => prev?.type === 'mission_progress' ? null : prev) }, 10000)
    }
    const progressIncreased = missions.some((m) => {
      const prev = prevMissions.find((pm) => pm.id === m.id)
      return prev && m.progress > prev.progress && m.progress < 100
    })
    if (progressIncreased) {
      const inProgress = activeMissions.find((m) => {
        const prev = prevMissions.find((pm) => pm.id === m.id)
        return prev && m.progress > prev.progress
      })
      if (inProgress) {
        const remainingSteps = inProgress.steps.filter((s) => !s.done).length
        if (remainingSteps > 0) {
          setObservation({ message: `Nice! ${remainingSteps} step${remainingSteps !== 1 ? 's' : ''} left on "${inProgress.title}".`, type: 'mission_progress' })
          setTimeout(() => { setObservation((prev) => prev?.type === 'mission_progress' ? null : prev) }, 8000)
        }
      }
    }
    prevMissionsRef.current = missions
  }, [missions])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const lastThread = localStorage.getItem('last-thread-title')
    if (lastThread) {
      setObservation({ message: `You left off on "${lastThread}". Want to continue?`, type: 'resume' })
      setTimeout(() => { setObservation((prev) => (prev?.type === 'resume' ? null : prev)) }, 15000)
    }
  }, [])

  return observation
}
