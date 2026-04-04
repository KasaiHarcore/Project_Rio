import { create } from 'zustand'
import { CharacterId } from '@/features/rio/types'

type ViewType = 'chat' | 'knowledge' | 'artifacts'
type ViewMode = 'dashboard' | 'operation'
export type AgentMode = 'chat' | 'rag' | 'web' | 'sql'

interface UIState {
  activeView: ViewType
  viewMode: ViewMode
  activeMissionId: string | null

  // Agent Mode
  agentMode: AgentMode

  userRole: 'user' | 'admin'


  sidebarOpen: boolean
  chatSidebarOpen: boolean
  chatKey: number

  splashSeen: boolean
  setSplashSeen: (seen: boolean) => void

  // Tutorial System
  isTutorialActive: boolean
  tutorialStep: number
  tutorialCompleted: boolean
  startTutorial: () => void
  nextTutorialStep: () => void
  endTutorial: () => void

  hydrateFromStorage: () => void

  setActiveView: (view: ViewType) => void
  setViewMode: (mode: ViewMode) => void
  setAgentMode: (mode: AgentMode) => void
  setUserRole: (role: 'user' | 'admin') => void

  startMission: (missionId?: string) => void
  endMission: () => void

  toggleSidebar: () => void
  toggleChatSidebar: () => void
  resetChat: () => void
}

export const useUIStore = create<UIState>((set) => ({
  activeView: 'chat',
  viewMode: 'dashboard',
  activeMissionId: null,

  agentMode: 'chat' as AgentMode, // Default agent mode

  userRole: 'user' as const, // Default role, hydrated from /auth/me


  sidebarOpen: true,
  chatSidebarOpen: true,
  chatKey: 0,

  splashSeen: false,
  setSplashSeen: (seen) => {
    try { localStorage.setItem('schale-splash-seen', String(seen)) } catch { }
    set({ splashSeen: seen })
  },

  isTutorialActive: false,
  tutorialStep: 0,
  tutorialCompleted: false,
  startTutorial: () => set({ isTutorialActive: true, tutorialStep: 0 }),
  nextTutorialStep: () => set((state) => ({ tutorialStep: state.tutorialStep + 1 })),
  endTutorial: () => {
    try { localStorage.setItem('schale-tutorial-completed', 'true') } catch { }
    set({ isTutorialActive: false, tutorialStep: 0, tutorialCompleted: true })
  },

  hydrateFromStorage: () => {
    if (typeof window === 'undefined') return
    try {
      const splash = localStorage.getItem('schale-splash-seen')
      const tutorial = localStorage.getItem('schale-tutorial-completed')
      set({
        ...(splash !== null ? { splashSeen: splash === 'true' } : {}),
        ...(tutorial !== null ? { tutorialCompleted: tutorial === 'true' } : {}),
      })
    } catch { }
  },

  setActiveView: (view) => set({ activeView: view }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setAgentMode: (mode) => set({ agentMode: mode }),
  setUserRole: (role) => set((state) => ({
    userRole: role,
    // Reset to chat if non-admin had SQL selected
    ...(role !== 'admin' && state.agentMode === 'sql' ? { agentMode: 'chat' as AgentMode } : {}),
  })),

  startMission: (missionId) => set({
    viewMode: 'operation',
    activeMissionId: missionId || 'new-operation',
    chatKey: Date.now()
  }),

  endMission: () => set({
    viewMode: 'dashboard',
    activeMissionId: null
  }),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleChatSidebar: () => set((state) => ({ chatSidebarOpen: !state.chatSidebarOpen })),
  resetChat: () => set((state) => ({ chatKey: state.chatKey + 1 })),
}))
