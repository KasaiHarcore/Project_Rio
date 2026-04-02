import { create } from 'zustand'
import {
  apiListAutomations, apiCreateAutomation, apiUpdateAutomation,
  apiDeleteAutomation, apiRunAutomation,
} from './api'
import type { Automation, AutomationCreate, AutomationUpdate } from './api'

interface AutomationState {
  automations: Automation[]
  loading: boolean
  running: Record<string, boolean>

  fetchAutomations: () => Promise<void>
  createAutomation: (data: AutomationCreate) => Promise<Automation | null>
  updateAutomation: (id: string, data: AutomationUpdate) => Promise<Automation | null>
  deleteAutomation: (id: string) => Promise<boolean>
  toggleEnabled: (id: string) => Promise<void>
  runAutomation: (id: string) => Promise<string | null>
}

export const useAutomationStore = create<AutomationState>((set, get) => ({
  automations: [],
  loading: false,
  running: {},

  fetchAutomations: async () => {
    set({ loading: true })
    try {
      const automations = await apiListAutomations()
      set({ automations })
    } catch { /* ignore */ } finally {
      set({ loading: false })
    }
  },

  createAutomation: async (data) => {
    try {
      const auto = await apiCreateAutomation(data)
      set((s) => ({ automations: [auto, ...s.automations] }))
      return auto
    } catch { return null }
  },

  updateAutomation: async (id, data) => {
    try {
      const auto = await apiUpdateAutomation(id, data)
      set((s) => ({ automations: s.automations.map((a) => a.id === id ? auto : a) }))
      return auto
    } catch { return null }
  },

  deleteAutomation: async (id) => {
    try {
      await apiDeleteAutomation(id)
      set((s) => ({ automations: s.automations.filter((a) => a.id !== id) }))
      return true
    } catch { return false }
  },

  toggleEnabled: async (id) => {
    const auto = get().automations.find((a) => a.id === id)
    if (!auto) return
    await get().updateAutomation(id, { enabled: !auto.enabled })
  },

  runAutomation: async (id) => {
    set((s) => ({ running: { ...s.running, [id]: true } }))
    try {
      const result = await apiRunAutomation(id)
      get().fetchAutomations()
      return result.answer
    } catch { return null } finally {
      set((s) => ({ running: { ...s.running, [id]: false } }))
    }
  },
}))
