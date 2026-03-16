import { create } from 'zustand'
import { apiFetch } from '@/shared/api/client'

/* ─── Types ──────────────────────────────────────────────────────── */

export type Mood = 'happy' | 'neutral' | 'sad' | 'excited' | 'frustrated' | 'tired'
export type RelationshipTier = 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'bonded'

export interface EmotionalState {
  mood: Mood
  energy: number
  affinity: number
  relationshipTier: RelationshipTier
  streakDays: number
  interactionCount: number
  moodChanged: boolean
  /** Timestamp of last update from backend */
  lastUpdatedAt: number
}

/* ─── Store ──────────────────────────────────────────────────────── */

interface EmotionalStore extends EmotionalState {
  /** Update from a streaming emotional_update event */
  applyUpdate: (update: {
    mood: string
    energy: number
    affinity: number
    relationship_tier: string
    mood_changed: boolean
    streak_days?: number
    interaction_count?: number
  }) => void

  /** Fetch full state from REST API */
  fetchState: (characterId: string) => Promise<void>

  /** Record a headpat via REST API */
  recordHeadpat: (characterId: string) => Promise<{
    mood: Mood
    affinity: number
    affinityDelta: number
    moodChanged: boolean
    animationCue: string
  } | null>
}

export const useEmotionalStore = create<EmotionalStore>((set) => ({
  // Default state
  mood: 'neutral',
  energy: 1.0,
  affinity: 0,
  relationshipTier: 'stranger',
  streakDays: 0,
  interactionCount: 0,
  moodChanged: false,
  lastUpdatedAt: 0,

  applyUpdate: (update) => {
    set({
      mood: update.mood as Mood,
      energy: update.energy,
      affinity: update.affinity,
      relationshipTier: update.relationship_tier as RelationshipTier,
      streakDays: update.streak_days ?? 0,
      interactionCount: update.interaction_count ?? 0,
      moodChanged: update.mood_changed,
      lastUpdatedAt: Date.now(),
    })
  },

  fetchState: async (characterId: string) => {
    try {
      const data = await apiFetch<{
        mood: string
        energy: number
        affinity: number
        relationship_tier: string
        streak_days: number
        interaction_count: number
      }>(`/emotional/state?character_id=${encodeURIComponent(characterId)}`)
      set({
        mood: data.mood as Mood,
        energy: data.energy,
        affinity: data.affinity,
        relationshipTier: data.relationship_tier as RelationshipTier,
        streakDays: data.streak_days,
        interactionCount: data.interaction_count,
        moodChanged: false,
        lastUpdatedAt: Date.now(),
      })
    } catch {
      // Silently fail — emotional state is non-critical
    }
  },

  recordHeadpat: async (characterId: string) => {
    try {
      const data = await apiFetch<{
        mood: string
        affinity: number
        affinity_delta: number
        mood_changed: boolean
        animation_cue: string
      }>('/emotional/headpat', {
        method: 'POST',
        body: JSON.stringify({ character_id: characterId }),
      })
      set({
        mood: data.mood as Mood,
        affinity: data.affinity,
        moodChanged: data.mood_changed,
        lastUpdatedAt: Date.now(),
      })
      return {
        mood: data.mood as Mood,
        affinity: data.affinity,
        affinityDelta: data.affinity_delta,
        moodChanged: data.mood_changed,
        animationCue: data.animation_cue,
      }
    } catch {
      return null
    }
  },
}))
