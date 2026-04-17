/**
 * Branch navigation store for conversation branching.
 *
 * Tracks which branch is selected at each fork point in the message tree.
 * Used by MissionControl to determine the active conversation path.
 */

import { create } from 'zustand'
import type { MessageNode } from '@/features/chat/lib/message-tree'

interface BranchState {
  /** Map of parentId (or "root") → selected child message ID */
  branchSelections: Map<string, string>

  /** Select a specific branch at a fork point */
  selectBranch: (parentId: string, childId: string) => void

  /**
   * Navigate to the next sibling at a fork point.
   * Requires the siblings array to determine ordering.
   */
  nextBranch: (parentId: string, siblings: MessageNode[]) => void

  /**
   * Navigate to the previous sibling at a fork point.
   * Requires the siblings array to determine ordering.
   */
  prevBranch: (parentId: string, siblings: MessageNode[]) => void

  /** Reset all branch selections (returns to latest-branch defaults) */
  resetSelections: () => void
}

export const useBranchStore = create<BranchState>((set) => ({
  branchSelections: new Map(),

  selectBranch: (parentId, childId) =>
    set((state) => {
      const next = new Map(state.branchSelections)
      next.set(parentId, childId)
      return { branchSelections: next }
    }),

  nextBranch: (parentId, siblings) =>
    set((state) => {
      if (siblings.length <= 1) return state

      const currentId = state.branchSelections.get(parentId)
      const currentIndex = currentId
        ? siblings.findIndex((s) => s.message.id === currentId)
        : siblings.length - 1 // default = latest

      const nextIndex = Math.min(currentIndex + 1, siblings.length - 1)
      if (nextIndex === currentIndex) return state

      const next = new Map(state.branchSelections)
      next.set(parentId, siblings[nextIndex].message.id)
      return { branchSelections: next }
    }),

  prevBranch: (parentId, siblings) =>
    set((state) => {
      if (siblings.length <= 1) return state

      const currentId = state.branchSelections.get(parentId)
      const currentIndex = currentId
        ? siblings.findIndex((s) => s.message.id === currentId)
        : siblings.length - 1

      const prevIndex = Math.max(currentIndex - 1, 0)
      if (prevIndex === currentIndex) return state

      const next = new Map(state.branchSelections)
      next.set(parentId, siblings[prevIndex].message.id)
      return { branchSelections: next }
    }),

  resetSelections: () => set({ branchSelections: new Map() }),
}))
