/**
 * note-confirmation-store.ts — Zustand store for Note HITL confirmation workflow.
 *
 * Holds the current pending note confirmation request (if any) and
 * tracks the "resuming" state while the backend processes the
 * user's decision.
 */

import { create } from 'zustand'

export interface NoteConfirmationRequest {
  confirmation_type: string // "note_delete_confirmation" | "note_update_confirmation"
  note_id: string
  note_title: string
  action: string // "delete" | "update"
  update_type?: string | null // "FULL_REWRITE" etc. (only for update)
  message: string
  options: string[]
}

interface NoteConfirmationState {
  /** The currently pending confirmation request, or null if none. */
  pending: NoteConfirmationRequest | null
  /** Thread ID for the pending confirmation. */
  threadId: string | null
  /** True while the resume request is in-flight. */
  isResuming: boolean

  setPending: (req: NoteConfirmationRequest, threadId: string) => void
  clear: () => void
  setResuming: (v: boolean) => void
}

export const useNoteConfirmationStore = create<NoteConfirmationState>((set) => ({
  pending: null,
  threadId: null,
  isResuming: false,

  setPending: (req, threadId) =>
    set({ pending: req, threadId, isResuming: false }),

  clear: () =>
    set({ pending: null, threadId: null, isResuming: false }),

  setResuming: (v) => set({ isResuming: v }),
}))
