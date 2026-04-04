import { create } from 'zustand'
import { apiListArtifacts, apiDeleteArtifact, type ArtifactRecord } from './api'

export type { ArtifactRecord }

/* ─── Store ──────────────────────────────────────────────────────── */

interface ArtifactState {
  artifacts: ArtifactRecord[]
  loading: boolean
  error: string | null

  /* Actions */
  fetchArtifacts: (threadId?: string, artifactType?: string) => Promise<void>
  addAgentArtifacts: (artifacts: Record<string, unknown>[], persistedIds?: string[]) => void
  deleteArtifact: (id: string) => Promise<boolean>
  reset: () => void
}

export const useArtifactStore = create<ArtifactState>((set, get) => ({
  artifacts: [],
  loading: false,
  error: null,

  fetchArtifacts: async (threadId, artifactType) => {
    set({ loading: true, error: null })
    try {
      const data = await apiListArtifacts(threadId, artifactType)
      set({ artifacts: Array.isArray(data) ? data : [], loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },

  addAgentArtifacts: (artifacts, persistedIds) => {
    const newRecords: ArtifactRecord[] = []
    for (let i = 0; i < artifacts.length; i++) {
      const a = artifacts[i]
      const id = persistedIds?.[i] ?? `tmp_${Date.now()}_${i}`
      newRecords.push({
        id,
        user_id: '',
        thread_id: (a.thread_id as string) ?? null,
        name: String(a.name ?? 'untitled'),
        artifact_type: String(a.artifact_type ?? 'code'),
        language: (a.language as string) ?? null,
        content: String(a.content ?? ''),
        version: (a.version as number) ?? 1,
        parent_id: (a.parent_id as string) ?? null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    }
    set((s) => ({ artifacts: [...newRecords, ...s.artifacts] }))
  },

  deleteArtifact: async (id) => {
    try {
      await apiDeleteArtifact(id)
      set((s) => ({ artifacts: s.artifacts.filter((a) => a.id !== id) }))
      return true
    } catch {
      return false
    }
  },

  reset: () => set({ artifacts: [], loading: false, error: null }),
}))
