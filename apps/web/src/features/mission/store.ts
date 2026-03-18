import { create } from 'zustand'

/* ─── Types ──────────────────────────────────────────────────────── */

export type MissionStatus = 'draft' | 'active' | 'completed' | 'archived'
export type MissionPriority = 'low' | 'normal' | 'critical'
export type MissionSource = 'agent' | 'user'

export interface MissionStep {
  text: string
  done: boolean
}

export interface Mission {
  id: string
  title: string
  description: string | null
  status: MissionStatus
  priority: MissionPriority
  source: MissionSource
  progress: number
  tags: string[]
  steps: MissionStep[]
  sort_order: number
  thread_id: string | null
  /* Notion-style scheduling */
  deadline: string | null
  scheduled_start: string | null
  estimated_minutes: number | null
  category: string | null
  notes: string | null
  meet_url: string | null
  /* Timestamps */
  created_at: string
  updated_at: string
}

export interface MissionStats {
  total: number
  active: number
  completed: number
  overdue: number
  categories: string[]
}

/* ─── Store ──────────────────────────────────────────────────────── */

interface MissionState {
  missions: Mission[]
  stats: MissionStats | null
  loading: boolean
  error: string | null
  /* View preferences */
  viewMode: 'board' | 'table' | 'calendar'
  filterCategory: string | null
  filterPriority: MissionPriority | null

  /* Actions */
  fetchMissions: (status?: MissionStatus) => Promise<void>
  fetchStats: () => Promise<void>
  createMission: (data: Partial<Mission>) => Promise<Mission | null>
  updateMission: (id: string, data: Partial<Mission>) => Promise<Mission | null>
  deleteMission: (id: string) => Promise<boolean>
  toggleStep: (missionId: string, stepIndex: number) => Promise<Mission | null>
  /** Called by chat-transport when agent creates missions in real-time */
  addAgentMissions: (raw: Array<Record<string, unknown>>, persistedIds?: string[]) => void
  /** Called by chat-transport when agent toggles a step or completes a mission */
  applyAgentAction: (action: string, mission: Record<string, unknown>, stepIndex?: number | null) => void
  /** Optimistic reorder (drag-and-drop) */
  reorderMissions: (fromIndex: number, toIndex: number) => void
  /** View preferences */
  setViewMode: (mode: 'board' | 'table' | 'calendar') => void
  setFilterCategory: (cat: string | null) => void
  setFilterPriority: (p: MissionPriority | null) => void
}

async function apiFetch<T>(
  path: string,
  opts?: RequestInit,
): Promise<T | null> {
  try {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    })
    if (!res.ok) return null
    if (res.status === 204) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

export const useMissionStore = create<MissionState>((set, get) => ({
  missions: [],
  stats: null,
  loading: false,
  error: null,
  viewMode: 'board',
  filterCategory: null,
  filterPriority: null,

  /* ── Fetch ── */
  fetchMissions: async (status) => {
    set({ loading: true, error: null })
    const qs = status ? `?status=${status}` : ''
    const data = await apiFetch<Mission[]>(`/api/missions${qs}`)
    set({
      missions: data ?? [],
      loading: false,
      error: data === null ? 'Failed to fetch missions' : null,
    })
  },

  /* ── Stats ── */
  fetchStats: async () => {
    const data = await apiFetch<MissionStats>('/api/missions/stats')
    if (data) set({ stats: data })
  },

  /* ── Create ── */
  createMission: async (data) => {
    const created = await apiFetch<Mission>('/api/missions', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    if (created) {
      set((s) => ({ missions: [created, ...s.missions] }))
      // Refresh stats
      get().fetchStats()
    }
    return created
  },

  /* ── Update ── */
  updateMission: async (id, data) => {
    const updated = await apiFetch<Mission>(`/api/missions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
    if (updated) {
      set((s) => ({
        missions: s.missions.map((m) => (m.id === id ? updated : m)),
      }))
      get().fetchStats()
    }
    return updated
  },

  /* ── Delete ── */
  deleteMission: async (id) => {
    const res = await fetch(`/api/missions/${id}`, { method: 'DELETE' })
    if (res.ok) {
      set((s) => ({ missions: s.missions.filter((m) => m.id !== id) }))
      get().fetchStats()
      return true
    }
    return false
  },

  /* ── Toggle Step ── */
  toggleStep: async (missionId, stepIndex) => {
    const updated = await apiFetch<Mission>(
      `/api/missions/${missionId}/steps/${stepIndex}/toggle`,
      { method: 'PATCH' },
    )
    if (updated) {
      set((s) => ({
        missions: s.missions.map((m) => (m.id === missionId ? updated : m)),
      }))
      get().fetchStats()
    }
    return updated
  },

  /* ── Agent-created (real-time from chat-transport) ── */
  addAgentMissions: (raw, persistedIds) => {
    const newMissions: Mission[] = raw
      .filter((m) => m.title)
      .map((m, i) => ({
        id: persistedIds?.[i] ?? `agent-${Date.now()}-${i}`,
        title: String(m.title ?? ''),
        description: String(m.description ?? '') || null,
        status: 'active' as MissionStatus,
        priority: (['low', 'normal', 'critical'].includes(String(m.priority ?? ''))
          ? String(m.priority)
          : 'normal') as MissionPriority,
        source: 'agent' as MissionSource,
        progress: 0,
        tags: Array.isArray(m.tags) ? (m.tags as string[]).map(String) : [],
        steps: Array.isArray(m.steps)
          ? (m.steps as Array<Record<string, unknown>>).map((s) => ({
            text: String(s.text ?? ''),
            done: Boolean(s.done),
          }))
          : [],
        sort_order: 0,
        thread_id: null,
        deadline: m.deadline ? String(m.deadline) : null,
        scheduled_start: null,
        estimated_minutes: typeof m.estimated_minutes === 'number' ? m.estimated_minutes : null,
        category: m.category ? String(m.category) : null,
        notes: null,
        meet_url: m.meet_url ? String(m.meet_url) : null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }))

    if (newMissions.length) {
      set((s) => ({ missions: [...newMissions, ...s.missions] }))
      get().fetchStats()
    }
  },

  /* ── Agent action (toggle step / complete / update / delete from SSE) ── */
  applyAgentAction: (action, mission, stepIndex) => {
    const missionId = String(mission.id ?? '')
    if (!missionId) return

    if (action === 'toggle_step' || action === 'complete_mission' || action === 'update_mission') {
      // Update the mission in-place with data from the backend
      set((s) => ({
        missions: s.missions.map((m) => {
          if (m.id !== missionId) return m
          return {
            ...m,
            ...(mission.title != null && { title: String(mission.title) }),
            ...(mission.description !== undefined && { description: mission.description ? String(mission.description) : null }),
            status: (mission.status as MissionStatus) ?? m.status,
            priority: (mission.priority as MissionPriority) ?? m.priority,
            progress: typeof mission.progress === 'number' ? mission.progress : m.progress,
            steps: Array.isArray(mission.steps)
              ? (mission.steps as Array<Record<string, unknown>>).map((step) => ({
                  text: String(step.text ?? ''),
                  done: Boolean(step.done),
                }))
              : m.steps,
            ...(mission.deadline !== undefined && { deadline: mission.deadline ? String(mission.deadline) : null }),
            ...(mission.category !== undefined && { category: mission.category ? String(mission.category) : null }),
            ...(mission.estimated_minutes !== undefined && {
              estimated_minutes: typeof mission.estimated_minutes === 'number' ? mission.estimated_minutes : null,
            }),
            ...(mission.tags !== undefined && {
              tags: Array.isArray(mission.tags) ? (mission.tags as string[]).map(String) : m.tags,
            }),
            updated_at: new Date().toISOString(),
          }
        }),
      }))
      get().fetchStats()
    } else if (action === 'delete_mission') {
      // Remove the mission from the list
      set((s) => ({
        missions: s.missions.filter((m) => m.id !== missionId),
      }))
      get().fetchStats()
    }
  },

  /* ── Reorder (drag-and-drop) ── */
  reorderMissions: (fromIndex, toIndex) => {
    set((s) => {
      const arr = [...s.missions]
      const [moved] = arr.splice(fromIndex, 1)
      arr.splice(toIndex, 0, moved)
      return { missions: arr }
    })
  },

  /* ── View preferences ── */
  setViewMode: (mode) => set({ viewMode: mode }),
  setFilterCategory: (cat) => set({ filterCategory: cat }),
  setFilterPriority: (p) => set({ filterPriority: p }),
}))
