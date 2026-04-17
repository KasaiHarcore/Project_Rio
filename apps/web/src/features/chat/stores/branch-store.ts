/**
 * Branch navigation store for conversation branching.
 *
 * Tracks which branch is selected at each fork point in the message tree.
 * Selections are scoped per-thread and persisted to localStorage so they
 * survive page reloads and don't leak across threads.
 */

import { create } from 'zustand'
import type { MessageNode } from '@/features/chat/lib/message-tree'

const STORAGE_KEY_PREFIX = 'rio:branch-selections:'

function storageKey(threadId: string): string {
  return STORAGE_KEY_PREFIX + threadId
}

function loadFromStorage(threadId: string | null): Map<string, string> {
  if (!threadId || typeof window === 'undefined') return new Map()
  try {
    const raw = window.localStorage.getItem(storageKey(threadId))
    if (!raw) return new Map()
    const entries = JSON.parse(raw) as [string, string][]
    if (!Array.isArray(entries)) return new Map()
    return new Map(entries)
  } catch {
    return new Map()
  }
}

function saveToStorage(threadId: string | null, selections: Map<string, string>): void {
  if (!threadId || typeof window === 'undefined') return
  try {
    if (selections.size === 0) {
      window.localStorage.removeItem(storageKey(threadId))
      return
    }
    const entries = Array.from(selections.entries())
    window.localStorage.setItem(storageKey(threadId), JSON.stringify(entries))
  } catch {
    // localStorage may be unavailable (private mode, quota, disabled) — non-fatal
  }
}

export interface PendingBranchParent {
  /** Message ID that will serve as parent_id for the NEXT sent message */
  messageId: string
  /** Short text preview of the parent message, for UI display */
  preview: string
  /** Role of the parent message, for UI styling */
  role: 'user' | 'assistant' | string
}

interface BranchState {
  /** Thread whose selections are currently loaded. null = no thread active. */
  activeThreadId: string | null

  /** Map of parentId (or "root") → selected child message ID for the active thread */
  branchSelections: Map<string, string>

  /**
   * Fork intent for the next user message. When set, the transport sends
   * `parent_message_id` on the next POST and this is cleared.
   */
  pendingBranchParent: PendingBranchParent | null

  /** Load selections for a thread (or clear when null). Called on thread switch. */
  setActiveThread: (threadId: string | null) => void

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

  /** Reset all branch selections for the active thread (returns to latest-branch defaults) */
  resetSelections: () => void

  /** Mark the next sent message as a branch from this parent. Pass null to cancel. */
  setPendingBranchParent: (parent: PendingBranchParent | null) => void

  /**
   * Read and atomically clear the pending branch parent. Called by the transport
   * when a new message is dispatched so the fork intent applies once only.
   */
  consumePendingBranchParent: () => PendingBranchParent | null
}

export const useBranchStore = create<BranchState>((set, get) => ({
  activeThreadId: null,
  branchSelections: new Map(),
  pendingBranchParent: null,

  setActiveThread: (threadId) => {
    if (get().activeThreadId === threadId) return
    set({
      activeThreadId: threadId,
      branchSelections: loadFromStorage(threadId),
      pendingBranchParent: null, // clear fork intent on thread switch
    })
  },

  selectBranch: (parentId, childId) =>
    set((state) => {
      const next = new Map(state.branchSelections)
      next.set(parentId, childId)
      saveToStorage(state.activeThreadId, next)
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
      saveToStorage(state.activeThreadId, next)
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
      saveToStorage(state.activeThreadId, next)
      return { branchSelections: next }
    }),

  resetSelections: () =>
    set((state) => {
      saveToStorage(state.activeThreadId, new Map())
      return { branchSelections: new Map() }
    }),

  setPendingBranchParent: (parent) => set({ pendingBranchParent: parent }),

  consumePendingBranchParent: () => {
    const current = get().pendingBranchParent
    if (current) set({ pendingBranchParent: null })
    return current
  },
}))
