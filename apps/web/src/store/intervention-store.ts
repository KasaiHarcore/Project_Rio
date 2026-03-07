import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/* ─── Types ──────────────────────────────────────────────────────── */

export type InterventionType =
  | 'toast'           // Gentle notification (5s auto-dismiss)
  | 'modal'           // Caring advice (requires interaction)
  | 'blocking'        // Aggressive intervention (blocks UI)
  | 'celebration'     // Achievement celebration
  | 're-engagement'   // Welcome back prompt

export interface InterventionMessage {
  id: string
  type: InterventionType
  message: string
  actions?: InterventionAction[]
  triggerReason: string
  timestamp: number
  countdown?: number // for blocking type
}

export interface InterventionAction {
  label: string
  action: 'dismiss' | 'accept' | 'override' | 'remind'
  affinityChange?: number
}

export interface InterventionPreferences {
  aggressiveness: 'gentle' | 'balanced' | 'aggressive'
  breakFrequency: 30 | 45 | 60 | 90 | 0 // minutes, 0 = off
  workHourLimits: boolean
  allowToast: boolean
  allowModal: boolean
  allowBlocking: boolean
}

/* ─── Store ──────────────────────────────────────────────────────── */

interface InterventionStore {
  // State
  currentIntervention: InterventionMessage | null
  interventionQueue: InterventionMessage[]
  dismissedInterventions: Set<string>
  lastInterventionTime: number
  preferences: InterventionPreferences

  // Actions
  triggerIntervention: (message: Omit<InterventionMessage, 'id' | 'timestamp'>) => void
  dismissIntervention: (id: string, affinityChange?: number) => void
  acceptIntervention: (id: string, affinityChange?: number) => void
  clearIntervention: () => void
  updatePreferences: (preferences: Partial<InterventionPreferences>) => void
  canTrigger: (type: InterventionType, reason: string) => boolean
}

export const useInterventionStore = create<InterventionStore>()(
  persist(
    (set, get) => ({
      // Initial state
      currentIntervention: null,
      interventionQueue: [],
      dismissedInterventions: new Set(),
      lastInterventionTime: 0,
      preferences: {
        aggressiveness: 'balanced',
        breakFrequency: 45,
        workHourLimits: true,
        allowToast: true,
        allowModal: true,
        allowBlocking: true,
      },

      // Trigger a new intervention
      triggerIntervention: (message) => {
        const { preferences, currentIntervention, canTrigger } = get()

        // Check preferences
        if (!canTrigger(message.type, message.triggerReason)) {
          return
        }

        const intervention: InterventionMessage = {
          ...message,
          id: `${message.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }

        // If there's already an intervention, queue this one (unless it's blocking)
        if (currentIntervention && message.type !== 'blocking') {
          set((state) => ({
            interventionQueue: [...state.interventionQueue, intervention],
          }))
          return
        }

        // Show intervention immediately
        set({
          currentIntervention: intervention,
          lastInterventionTime: Date.now(),
        })
      },

      // Dismiss intervention
      dismissIntervention: (id, affinityChange = 0) => {
        const { currentIntervention, interventionQueue } = get()

        if (currentIntervention?.id === id) {
          // Add to dismissed set
          set((state) => ({
            dismissedInterventions: new Set(state.dismissedInterventions).add(id),
            currentIntervention: null,
          }))

          // Apply affinity change if any
          if (affinityChange !== 0) {
            // This would trigger the emotional store update
            // We'll handle this in the component
          }

          // Show next queued intervention
          if (interventionQueue.length > 0) {
            const [next, ...rest] = interventionQueue
            set({
              currentIntervention: next,
              interventionQueue: rest,
            })
          }
        }
      },

      // Accept intervention
      acceptIntervention: (id, affinityChange = 0) => {
        const { currentIntervention, interventionQueue } = get()

        if (currentIntervention?.id === id) {
          set({ currentIntervention: null })

          // Apply affinity change
          if (affinityChange !== 0) {
            // Handle in component
          }

          // Show next queued intervention
          if (interventionQueue.length > 0) {
            const [next, ...rest] = interventionQueue
            set({
              currentIntervention: next,
              interventionQueue: rest,
            })
          }
        }
      },

      // Clear current intervention
      clearIntervention: () => {
        set({ currentIntervention: null })
      },

      // Update preferences
      updatePreferences: (newPreferences) => {
        set((state) => ({
          preferences: { ...state.preferences, ...newPreferences },
        }))
      },

      // Check if intervention can be triggered
      canTrigger: (type, reason) => {
        const { preferences, lastInterventionTime, dismissedInterventions } = get()

        // Check type-specific preferences
        if (type === 'toast' && !preferences.allowToast) return false
        if (type === 'modal' && !preferences.allowModal) return false
        if (type === 'blocking' && !preferences.allowBlocking) return false

        // Cooldown: Don't spam interventions (at least 30s between)
        const timeSinceLastIntervention = Date.now() - lastInterventionTime
        if (timeSinceLastIntervention < 30000 && type !== 'blocking') return false

        // Check if same reason was dismissed recently (within 30 minutes)
        const recentDismissals = Array.from(dismissedInterventions).filter((id) =>
          id.includes(reason)
        )
        if (recentDismissals.length > 0) {
          const lastDismissalId = recentDismissals[recentDismissals.length - 1]
          const timestamp = parseInt(lastDismissalId.split('-')[1] || '0')
          if (Date.now() - timestamp < 30 * 60 * 1000) return false
        }

        return true
      },
    }),
    {
      name: 'intervention-storage',
      partialize: (state) => ({
        preferences: state.preferences,
        dismissedInterventions: Array.from(state.dismissedInterventions),
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Convert dismissed interventions array back to Set
          state.dismissedInterventions = new Set(state.dismissedInterventions as any)
        }
      },
    }
  )
)
