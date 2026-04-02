/**
 * useActivityMonitor - Tracks user activity patterns
 *
 * Monitors:
 * - Session duration (for break reminders)
 * - Idle time (for check-ins)
 * - Time of day (for late-night warnings)
 * - Activity patterns (productive hours, weekend work)
 */

import { useState, useEffect, useRef, useCallback } from 'react'

export interface ActivityData {
  sessionDuration: number // milliseconds since session start
  lastActivityTime: number // timestamp of last activity
  idleTime: number // milliseconds since last activity
  isIdle: boolean // idle > 10 minutes
  isLateNight: boolean // 12am-5am
  isWeekend: boolean
  eventCount: number // total events this session
}

const IDLE_THRESHOLD = 10 * 60 * 1000 // 10 minutes

export function useActivityMonitor() {
  const [activityData, setActivityData] = useState<ActivityData>({
    sessionDuration: 0,
    lastActivityTime: Date.now(),
    idleTime: 0,
    isIdle: false,
    isLateNight: false,
    isWeekend: false,
    eventCount: 0,
  })

  const sessionStartRef = useRef(Date.now())
  const lastActivityRef = useRef(Date.now())
  const eventCountRef = useRef(0)

  // Track activity events (throttled — only update ref, no re-render)
  const updateActivity = useCallback(() => {
    lastActivityRef.current = Date.now()
    eventCountRef.current += 1
  }, [])

  // Listen to user activity events
  useEffect(() => {
    // Throttle mousemove to avoid excessive calls
    let moveTimer: ReturnType<typeof setTimeout> | null = null
    const throttledMove = () => {
      if (moveTimer) return
      moveTimer = setTimeout(() => { moveTimer = null }, 500)
      updateActivity()
    }

    const directEvents = ['keydown', 'click', 'scroll', 'touchstart'] as const
    directEvents.forEach((event) => {
      window.addEventListener(event, updateActivity, { passive: true })
    })
    window.addEventListener('mousemove', throttledMove, { passive: true })

    return () => {
      directEvents.forEach((event) => {
        window.removeEventListener(event, updateActivity)
      })
      window.removeEventListener('mousemove', throttledMove)
      if (moveTimer) clearTimeout(moveTimer)
    }
  }, [updateActivity])

  // Update state at a relaxed interval (10s instead of 1s)
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const sessionDuration = now - sessionStartRef.current
      const idleTime = now - lastActivityRef.current
      const isIdle = idleTime > IDLE_THRESHOLD

      const hour = new Date().getHours()
      const isLateNight = hour >= 0 && hour < 5

      const day = new Date().getDay()
      const isWeekend = day === 0 || day === 6

      setActivityData({
        sessionDuration,
        lastActivityTime: lastActivityRef.current,
        idleTime,
        isIdle,
        isLateNight,
        isWeekend,
        eventCount: eventCountRef.current,
      })
    }, 10_000)

    return () => clearInterval(interval)
  }, [])

  // Reset session duration
  const resetSession = useCallback(() => {
    sessionStartRef.current = Date.now()
    lastActivityRef.current = Date.now()
    eventCountRef.current = 0
  }, [])

  return {
    ...activityData,
    resetSession,
  }
}
