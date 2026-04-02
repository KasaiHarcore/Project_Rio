import { create } from 'zustand'
import { apiListAudio, apiGetAudio, apiGenerateAudio, apiDeleteAudio } from './api'
import type { AudioOverview, AudioGenerateRequest } from './api'

interface AudioState {
  overviews: AudioOverview[]
  loading: boolean
  generating: boolean

  fetchOverviews: () => Promise<void>
  generateAudio: (data: AudioGenerateRequest) => Promise<AudioOverview | null>
  deleteOverview: (id: string) => Promise<boolean>
  pollStatus: (id: string) => void
}

export const useAudioStore = create<AudioState>((set, get) => ({
  overviews: [],
  loading: false,
  generating: false,

  fetchOverviews: async () => {
    set({ loading: true })
    try {
      const overviews = await apiListAudio()
      set({ overviews })
    } catch { /* ignore */ } finally {
      set({ loading: false })
    }
  },

  generateAudio: async (data) => {
    set({ generating: true })
    try {
      const overview = await apiGenerateAudio(data)
      set((s) => ({ overviews: [overview, ...s.overviews] }))
      get().pollStatus(overview.id)
      return overview
    } catch { return null } finally {
      set({ generating: false })
    }
  },

  deleteOverview: async (id) => {
    try {
      await apiDeleteAudio(id)
      set((s) => ({ overviews: s.overviews.filter((o) => o.id !== id) }))
      return true
    } catch { return false }
  },

  pollStatus: (id) => {
    const interval = setInterval(async () => {
      try {
        const updated = await apiGetAudio(id)
        set((s) => ({
          overviews: s.overviews.map((o) => o.id === id ? updated : o),
        }))
        if (updated.status === 'ready' || updated.status === 'failed') {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 3000)
  },
}))
