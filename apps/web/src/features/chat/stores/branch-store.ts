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
const NAMES_STORAGE_KEY_PREFIX = 'rio:branch-names:'

function storageKey(threadId: string): string {
  return STORAGE_KEY_PREFIX + threadId
}

function namesStorageKey(threadId: string): string {
  return NAMES_STORAGE_KEY_PREFIX + threadId
}

function loadMapFromStorage(key: string): Map<string, string> {
  if (typeof window === 'undefined') return new Map()
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return new Map()
    const entries = JSON.parse(raw) as [string, string][]
    if (!Array.isArray(entries)) return new Map()
    return new Map(entries)
  } catch {
    return new Map()
  }
}

function saveMapToStorage(key: string, m: Map<string, string>): void {
  if (typeof window === 'undefined') return
  try {
    if (m.size === 0) {
      window.localStorage.removeItem(key)
      return
    }
    window.localStorage.setItem(key, JSON.stringify(Array.from(m.entries())))
  } catch {
    // localStorage may be unavailable (private mode, quota, disabled) — non-fatal
  }
}

function loadFromStorage(threadId: string | null): Map<string, string> {
  if (!threadId) return new Map()
  return loadMapFromStorage(storageKey(threadId))
}

function saveToStorage(threadId: string | null, selections: Map<string, string>): void {
  if (!threadId) return
  saveMapToStorage(storageKey(threadId), selections)
}

function loadNamesFromStorage(threadId: string | null): Map<string, string> {
  if (!threadId) return new Map()
  return loadMapFromStorage(namesStorageKey(threadId))
}

function saveNamesToStorage(threadId: string | null, names: Map<string, string>): void {
  if (!threadId) return
  saveMapToStorage(namesStorageKey(threadId), names)
}

interface BranchState {
  /** Thread whose selections are currently loaded. null = no thread active. */
  activeThreadId: string | null

  /** Map of parentId (or "root") → selected child message ID for the active thread */
  branchSelections: Map<string, string>

  /**
   * User-supplied names for branches, keyed by the branch-root message id.
   * Scoped per-thread; persisted to localStorage alongside branchSelections.
   */
  branchNames: Map<string, string>

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

  /** Set (or clear, with empty string) a user-supplied name for a branch. */
  setBranchName: (branchRootId: string, name: string) => void
}

export const useBranchStore = create<BranchState>((set) => ({
  activeThreadId: null,
  branchSelections: new Map(),
  branchNames: new Map(),

  setActiveThread: (threadId) => {
    if (useBranchStore.getState().activeThreadId === threadId) return
    set({
      activeThreadId: threadId,
      branchSelections: loadFromStorage(threadId),
      branchNames: loadNamesFromStorage(threadId),
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

  setBranchName: (branchRootId, name) =>
    set((state) => {
      const next = new Map(state.branchNames)
      const trimmed = name.trim()
      if (trimmed.length === 0) {
        next.delete(branchRootId)
      } else {
        next.set(branchRootId, trimmed)
      }
      saveNamesToStorage(state.activeThreadId, next)
      return { branchNames: next }
    }),
}))
