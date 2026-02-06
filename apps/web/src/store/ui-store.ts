import { create } from 'zustand'
import { CharacterId } from '@/types/character'

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
  
  splashSeen: false,
  setSplashSeen: (seen) => set({ splashSeen: seen }),

  isTutorialActive: false,
  tutorialStep: 0,
  startTutorial: () => set({ isTutorialActive: true, tutorialStep: 0 }),
  nextTutorialStep: () => set((state) => ({ tutorialStep: state.tutorialStep + 1 })),
  endTutorial: () => set({ isTutorialActive: false, tutorialStep: 0 }),

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
