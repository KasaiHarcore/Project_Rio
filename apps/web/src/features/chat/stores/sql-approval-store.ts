/**
 * sql-approval-store.ts — Zustand store for SQL HITL approval workflow.
 *
 * Holds the current pending SQL approval request (if any) and
 * tracks the "resuming" state while the backend processes the
 * user's decision.
 */

import { create } from 'zustand'

export interface SQLApprovalRequest {
  request_id: string
  sql: string
  natural_query: string
  operation_type: string
  danger_level: string
  affected_tables: string[]
  estimated_rows_affected?: string | null
  warnings: string[]
  explanation: string
  message: string
}

interface SQLApprovalState {
  /** The currently pending approval request, or null if none. */
  pending: SQLApprovalRequest | null
  /** Thread ID for the pending approval. */
  threadId: string | null
  /** True while the resume request is in-flight. */
  isResuming: boolean

  setPending: (req: SQLApprovalRequest, threadId: string) => void
  clear: () => void
  setResuming: (v: boolean) => void
}

export const useSQLApprovalStore = create<SQLApprovalState>((set) => ({
  pending: null,
  threadId: null,
  isResuming: false,

  setPending: (req, threadId) =>
    set({ pending: req, threadId, isResuming: false }),

  clear: () =>
    set({ pending: null, threadId: null, isResuming: false }),

  setResuming: (v) => set({ isResuming: v }),
}))
