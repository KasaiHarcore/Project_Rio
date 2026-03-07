/**
 * useAffinityTracker - Client-side affinity tracking and rewards
 *
 * Tracks user actions and awards affinity points:
 * - Session duration: +3 affinity every 30 minutes
 * - Absence penalty: -5 affinity if last login > 48 hours ago
 * - Mission step completion: +2 affinity per step
 * - Chat message: +1 affinity per message
 * - Document upload: +1 affinity per upload
 */

import { useEffect, useRef, useCallback } from 'react'
import { useEmotionalStore } from '@/store/emotional-store'

const SESSION_REWARD_INTERVAL = 30 * 60 * 1000 // 30 minutes
const SESSION_REWARD_AMOUNT = 3
const ABSENCE_THRESHOLD = 48 * 60 * 60 * 1000 // 48 hours
const ABSENCE_PENALTY = 5

const STORAGE_KEY_LAST_LOGIN = 'rio-last-login'
const STORAGE_KEY_SESSION_START = 'rio-session-start'

export function useAffinityTracker() {
  const applyUpdate = useEmotionalStore((state) => state.applyUpdate)
  const affinity = useEmotionalStore((state) => state.affinity)
  const sessionStartRef = useRef<number | null>(null)
  const rewardTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Check for absence penalty on mount
  useEffect(() => {
    if (typeof window === 'undefined') return

    const lastLogin = localStorage.getItem(STORAGE_KEY_LAST_LOGIN)
    const now = Date.now()

    if (lastLogin) {
      const timeSinceLastLogin = now - parseInt(lastLogin, 10)

      if (timeSinceLastLogin > ABSENCE_THRESHOLD) {
        // Apply absence penalty
        const newAffinity = Math.max(0, affinity - ABSENCE_PENALTY)
        applyUpdate({
          mood: 'sad',
          energy: 0.8,
          affinity: newAffinity,
          relationship_tier: calculateTier(newAffinity),
          mood_changed: true,
        })
      }
    }

    // Update last login time
    localStorage.setItem(STORAGE_KEY_LAST_LOGIN, now.toString())
  }, []) // Only run once on mount

  // Track session duration and award periodic bonuses
  useEffect(() => {
    if (typeof window === 'undefined') return

    const sessionStart = sessionStartRef.current || Date.now()
    sessionStartRef.current = sessionStart
    localStorage.setItem(STORAGE_KEY_SESSION_START, sessionStart.toString())

    // Set up interval to check for 30-minute milestones
    rewardTimerRef.current = setInterval(() => {
      const now = Date.now()
      const sessionDuration = now - sessionStart
      const intervals = Math.floor(sessionDuration / SESSION_REWARD_INTERVAL)

      // Award bonus for each 30-minute interval (only once per interval)
      const lastRewardedInterval = parseInt(
        localStorage.getItem('rio-last-reward-interval') || '0',
        10
      )

      if (intervals > lastRewardedInterval) {
        const newAffinity = Math.min(1000, affinity + SESSION_REWARD_AMOUNT)
        applyUpdate({
          mood: 'happy',
          energy: 1.0,
          affinity: newAffinity,
          relationship_tier: calculateTier(newAffinity),
          mood_changed: false,
        })
        localStorage.setItem('rio-last-reward-interval', intervals.toString())
      }
    }, 60000) // Check every minute

    return () => {
      if (rewardTimerRef.current) {
        clearInterval(rewardTimerRef.current)
      }
    }
  }, [affinity, applyUpdate])

  // Record mission step completion
  const recordMissionStep = useCallback(() => {
    const newAffinity = Math.min(1000, affinity + 2)
    applyUpdate({
      mood: 'happy',
      energy: 1.0,
      affinity: newAffinity,
      relationship_tier: calculateTier(newAffinity),
      mood_changed: false,
    })
  }, [affinity, applyUpdate])

  // Record chat message sent
  const recordMessage = useCallback(() => {
    const newAffinity = Math.min(1000, affinity + 1)
    applyUpdate({
      mood: 'neutral',
      energy: 1.0,
      affinity: newAffinity,
      relationship_tier: calculateTier(newAffinity),
      mood_changed: false,
    })
  }, [affinity, applyUpdate])

  // Record document upload
  const recordUpload = useCallback(() => {
    const newAffinity = Math.min(1000, affinity + 1)
    applyUpdate({
      mood: 'happy',
      energy: 1.0,
      affinity: newAffinity,
      relationship_tier: calculateTier(newAffinity),
      mood_changed: false,
    })
  }, [affinity, applyUpdate])

  return {
    recordMissionStep,
    recordMessage,
    recordUpload,
  }
}

// Helper to calculate relationship tier from affinity
function calculateTier(affinity: number): string {
  if (affinity >= 800) return 'bonded'
  if (affinity >= 600) return 'close_friend'
  if (affinity >= 300) return 'friend'
  if (affinity >= 100) return 'acquaintance'
  return 'stranger'
}
