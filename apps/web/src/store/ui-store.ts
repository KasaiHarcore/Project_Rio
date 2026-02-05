import { create } from 'zustand'

type ViewType = 'chat' | 'knowledge' | 'artifacts'

interface UIState {
  activeView: ViewType
  sidebarOpen: boolean
  setActiveView: (view: ViewType) => void
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>((set) => ({
  activeView: 'chat',
  sidebarOpen: true,
  setActiveView: (view) => set({ activeView: view }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}))
