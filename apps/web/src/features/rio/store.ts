import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/* ─── Types ──────────────────────────────────────────────────────── */

export type InterventionType =
  | 'toast'
  | 'modal'
  | 'blocking'
  | 'celebration'
  | 're-engagement'

export interface InterventionMessage {
  id: string
  type: InterventionType
  message: string
  actions?: InterventionAction[]
  triggerReason: string
  timestamp: number
  countdown?: number
}

export interface InterventionAction {
  label: string
  action: 'dismiss' | 'accept' | 'override' | 'remind'
  affinityChange?: number
}

export interface InterventionPreferences {
  aggressiveness: 'gentle' | 'balanced' | 'aggressive'
  breakFrequency: 30 | 45 | 60 | 90 | 0
  workHourLimits: boolean
  allowToast: boolean
  allowModal: boolean
  allowBlocking: boolean
}

/* ─── Store ──────────────────────────────────────────────────────── */

interface InterventionStore {
  currentIntervention: InterventionMessage | null
  interventionQueue: InterventionMessage[]
  dismissedInterventions: Set<string>
  lastInterventionTime: number
  preferences: InterventionPreferences

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

      triggerIntervention: (message) => {
        const { preferences, currentIntervention, canTrigger } = get()
        if (!canTrigger(message.type, message.triggerReason)) return

        const intervention: InterventionMessage = {
          ...message,
          id: `${message.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }

        if (currentIntervention && message.type !== 'blocking') {
          set((state) => ({ interventionQueue: [...state.interventionQueue, intervention] }))
          return
        }

        set({ currentIntervention: intervention, lastInterventionTime: Date.now() })
      },

      dismissIntervention: (id, affinityChange = 0) => {
        const { currentIntervention, interventionQueue } = get()
        if (currentIntervention?.id === id) {
          set((state) => ({
            dismissedInterventions: new Set(state.dismissedInterventions).add(id),
            currentIntervention: null,
          }))
          if (interventionQueue.length > 0) {
            const [next, ...rest] = interventionQueue
            set({ currentIntervention: next, interventionQueue: rest })
          }
        }
      },

      acceptIntervention: (id, affinityChange = 0) => {
        const { currentIntervention, interventionQueue } = get()
        if (currentIntervention?.id === id) {
          set({ currentIntervention: null })
          if (interventionQueue.length > 0) {
            const [next, ...rest] = interventionQueue
            set({ currentIntervention: next, interventionQueue: rest })
          }
        }
      },

      clearIntervention: () => set({ currentIntervention: null }),

      updatePreferences: (newPreferences) => {
        set((state) => ({ preferences: { ...state.preferences, ...newPreferences } }))
      },

      canTrigger: (type, reason) => {
        const { preferences, lastInterventionTime, dismissedInterventions } = get()
        if (type === 'toast' && !preferences.allowToast) return false
        if (type === 'modal' && !preferences.allowModal) return false
        if (type === 'blocking' && !preferences.allowBlocking) return false

        const timeSinceLastIntervention = Date.now() - lastInterventionTime
        if (timeSinceLastIntervention < 30000 && type !== 'blocking') return false

        const recentDismissals = Array.from(dismissedInterventions).filter((id) => id.includes(reason))
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
          state.dismissedInterventions = new Set(state.dismissedInterventions as any)
        }
      },
    }
  )
)
