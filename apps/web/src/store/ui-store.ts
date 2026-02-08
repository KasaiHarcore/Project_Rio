import { create } from 'zustand'
import { CharacterId } from '@/types/character'

// Safe localStorage helpers
const getStoredBoolean = (key: string, fallback: boolean): boolean => {
  if (typeof window === 'undefined') return fallback
  try {
    const stored = localStorage.getItem(key)
    return stored !== null ? stored === 'true' : fallback
  } catch { return fallback }
}

type ViewType = 'chat' | 'knowledge' | 'artifacts'
type ViewMode = 'dashboard' | 'operation'

interface UIState {
  // User Stats (RPG Elements)
  userLevel: number
  currentAp: number
  maxAp: number
  credits: number

  // Navigation View (Sidebar)
  activeView: ViewType
  // Main Content Mode
  viewMode: ViewMode
  activeMissionId: string | null
  
  // Character System
  activeCharacterId: CharacterId
  
  sidebarOpen: boolean
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

  setActiveView: (view: ViewType) => void
  setViewMode: (mode: ViewMode) => void
  setActiveCharacter: (characterId: CharacterId) => void // New Action
  
  startMission: (missionId?: string) => void
  endMission: () => void
  
  toggleSidebar: () => void
  resetChat: () => void
}

export const useUIStore = create<UIState>((set) => ({
  // User Stats Defaults
  userLevel: 54,
  currentAp: 120,
  maxAp: 120,
  credits: 1400200,

  activeView: 'chat',
  viewMode: 'dashboard', 
  activeMissionId: null,
  
  activeCharacterId: 'arona', // Default character
  
  sidebarOpen: true,
  chatKey: 0,
  
  splashSeen: getStoredBoolean('schale-splash-seen', false),
  setSplashSeen: (seen) => {
    try { localStorage.setItem('schale-splash-seen', String(seen)) } catch {}
    set({ splashSeen: seen })
  },

  isTutorialActive: false,
  tutorialStep: 0,
  tutorialCompleted: getStoredBoolean('schale-tutorial-completed', false),
  startTutorial: () => set({ isTutorialActive: true, tutorialStep: 0 }),
  nextTutorialStep: () => set((state) => ({ tutorialStep: state.tutorialStep + 1 })),
  endTutorial: () => {
    try { localStorage.setItem('schale-tutorial-completed', 'true') } catch {}
    set({ isTutorialActive: false, tutorialStep: 0, tutorialCompleted: true })
  },

  setActiveView: (view) => set({ activeView: view }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setActiveCharacter: (id) => set({ activeCharacterId: id }),
  
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
  resetChat: () => set((state) => ({ chatKey: state.chatKey + 1 })),
}))
