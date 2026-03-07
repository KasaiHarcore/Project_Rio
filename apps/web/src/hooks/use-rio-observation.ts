/**
 * useRioObservation - Context-aware Rio observations
 *
 * Detects user behavior patterns and returns appropriate observations:
 * - Idle detection: 10+ minutes no activity → "You've been quiet. Stuck?"
 * - Mission completion: When a mission is marked complete → "Good progress. X steps remaining."
 * - Long session: 45/90/120+ minutes → "Long session. Consider a break."
 * - Resume prompt: On mount, show last thread title → "You left off on [title]."
 * - Late-night work: 12am-5am → "It's very late. Consider getting sleep."
 * - Deadline pressure: <3 hours → "Mission due soon!"
 */

import { useState, useEffect, useRef } from 'react'
import { useMissionStore } from '@/store/mission-store'

const IDLE_THRESHOLD = 10 * 60 * 1000 // 10 minutes
const LONG_SESSION_THRESHOLD_1 = 45 * 60 * 1000 // 45 minutes
const LONG_SESSION_THRESHOLD_2 = 90 * 60 * 1000 // 90 minutes
const LONG_SESSION_THRESHOLD_3 = 120 * 60 * 1000 // 120 minutes

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

  // Track user activity (mouse, keyboard, clicks)
  useEffect(() => {
    const updateActivity = () => {
      setLastActivityTime(Date.now())
      // Clear idle observation when user becomes active
      setObservation((prev) => (prev?.type === 'idle' ? null : prev))
    }

    // Listen to various user events
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
    events.forEach((event) => {
      window.addEventListener(event, updateActivity)
    })

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, updateActivity)
      })
    }
  }, [])

  // Check for idle state periodically
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const timeSinceActivity = now - lastActivityTime

      // Idle detection
      if (timeSinceActivity > IDLE_THRESHOLD) {
        setObservation({
          message: "You've been quiet for a while. Stuck on something?",
          type: 'idle',
        })
      }

      // Long session detection (multi-level)
      const sessionDuration = now - sessionStartRef.current
      if (sessionDuration > LONG_SESSION_THRESHOLD_3) {
        setObservation({
          message: "Critical: 2 hours without a break. This is unhealthy. Please rest immediately.",
          type: 'long_session',
        })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_3 / 2)
      } else if (sessionDuration > LONG_SESSION_THRESHOLD_2) {
        setObservation({
          message: "Long session detected (90+ minutes). Time for a proper break.",
          type: 'long_session',
        })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_2 / 2)
      } else if (sessionDuration > LONG_SESSION_THRESHOLD_1) {
        setObservation({
          message: "You've been focused for 45 minutes. Great work! Consider a quick break.",
          type: 'long_session',
        })
        sessionStartRef.current = now - (LONG_SESSION_THRESHOLD_1 / 2)
      }

      // Late-night work detection (12am-5am)
      const hour = new Date().getHours()
      if (hour >= 0 && hour < 5 && sessionDuration > 15 * 60 * 1000) {
        setObservation({
          message: "It's very late (past midnight). Working now can harm your health. Please sleep.",
          type: 'late_night',
        })
      }
    }, 60000) // Check every minute

    return () => clearInterval(interval)
  }, [lastActivityTime])

  // Detect mission completion
  useEffect(() => {
    const prevMissions = prevMissionsRef.current
    const activeMissions = missions.filter((m) => m.status === 'active')
    const prevActiveMissions = prevMissions.filter((m) => m.status === 'active')

    // Check if any mission was just completed
    const newlyCompleted = prevMissions.find((pm) => {
      const current = missions.find((m) => m.id === pm.id)
      return (
        pm.status === 'active' &&
        current &&
        current.status === 'completed'
      )
    })

    if (newlyCompleted) {
      const remaining = activeMissions.length
      if (remaining > 0) {
        setObservation({
          message: `Good progress on "${newlyCompleted.title}". ${remaining} active mission${remaining !== 1 ? 's' : ''} remaining.`,
          type: 'mission_progress',
        })
      } else {
        setObservation({
          message: `Mission complete! All tasks cleared. Time to relax?`,
          type: 'mission_progress',
        })
      }

      // Auto-clear after 10 seconds
      setTimeout(() => {
        setObservation((prev) =>
          prev?.type === 'mission_progress' ? null : prev
        )
      }, 10000)
    }

    // Check if mission progress increased
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
          setObservation({
            message: `Nice! ${remainingSteps} step${remainingSteps !== 1 ? 's' : ''} left on "${inProgress.title}".`,
            type: 'mission_progress',
          })

          setTimeout(() => {
            setObservation((prev) =>
              prev?.type === 'mission_progress' ? null : prev
            )
          }, 8000)
        }
      }
    }

    prevMissionsRef.current = missions
  }, [missions])

  // Resume prompt on mount
  useEffect(() => {
    if (typeof window === 'undefined') return

    const lastThread = localStorage.getItem('last-thread-title')
    if (lastThread) {
      setObservation({
        message: `You left off on "${lastThread}". Want to continue?`,
        type: 'resume',
      })

      // Auto-clear after 15 seconds
      setTimeout(() => {
        setObservation((prev) => (prev?.type === 'resume' ? null : prev))
      }, 15000)
    }
  }, [])

  return observation
}
