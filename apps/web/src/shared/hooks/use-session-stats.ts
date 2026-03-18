/**
 * useSessionStats - Track session activity statistics
 *
 * Tracks:
 * - sessionDuration: Time since session started (in seconds)
 * - messagesThisSession: Count of messages sent this session
 * - missionsCompletedToday: Count of missions completed today
 *
 * Note: These stats are also available from the backend briefing API,
 * but this hook provides real-time local tracking.
 */

import { useState, useEffect } from 'react'
import { useMissionStore } from '@/features/mission/store'

const STORAGE_KEY_SESSION_START = 'rio-session-start'
const STORAGE_KEY_MESSAGES_COUNT = 'rio-messages-count'

export function useSessionStats() {
  const [sessionDuration, setSessionDuration] = useState(0)
  const [messagesThisSession, setMessagesThisSession] = useState(0)
  const missions = useMissionStore((state) => state.missions)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const stored = localStorage.getItem(STORAGE_KEY_SESSION_START)
    const sessionStart = stored ? parseInt(stored, 10) : Date.now()

    if (!stored) {
      localStorage.setItem(STORAGE_KEY_SESSION_START, sessionStart.toString())
    }

    const interval = setInterval(() => {
      const now = Date.now()
      const durationMs = now - sessionStart
      setSessionDuration(Math.floor(durationMs / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Load message count from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return

    const stored = localStorage.getItem(STORAGE_KEY_MESSAGES_COUNT)
    const count = stored ? parseInt(stored, 10) : 0
    setMessagesThisSession(count)
  }, [])

  // Calculate missions completed today
  const missionsCompletedToday = missions.filter((m) => {
    if (m.status !== 'completed') return false
    const updated = new Date(m.updated_at)
    const today = new Date()
    return (
      updated.getDate() === today.getDate() &&
      updated.getMonth() === today.getMonth() &&
      updated.getFullYear() === today.getFullYear()
    )
  }).length

  // Helper to increment message count (call when sending a message)
  const incrementMessages = () => {
    const newCount = messagesThisSession + 1
    setMessagesThisSession(newCount)
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY_MESSAGES_COUNT, newCount.toString())
    }
  }

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  return {
    sessionDuration,
    sessionDurationFormatted: formatDuration(sessionDuration),
    messagesThisSession,
    missionsCompletedToday,
    incrementMessages,
  }
}
