import { create } from "zustand"
import { apiExecuteShell, apiClassifyCommand } from "./api"
import type {
  CommandHistoryEntry,
  RiskTier,
  ShellClassifyResult,
  ShellResult,
} from "./types"

/* ─── Store ──────────────────────────────────────────────────────── */

interface OSControlState {
  history: CommandHistoryEntry[]
  currentDir: string
  isRunning: boolean
  pendingApproval: { id: string; command: string; classification: ShellClassifyResult } | null
  error: string | null

  /* Actions */
  executeCommand: (command: string) => Promise<void>
  classifyCommand: (command: string) => Promise<ShellClassifyResult>
  approveAndRun: () => Promise<void>
  rejectPending: () => void
  clearHistory: () => void
}

let _nextId = 0
const makeId = () => `cmd_${Date.now()}_${_nextId++}`

export const useOSControlStore = create<OSControlState>((set, get) => ({
  history: [],
  currentDir: "~",
  isRunning: false,
  pendingApproval: null,
  error: null,

  classifyCommand: async (command: string) => {
    return apiClassifyCommand(command)
  },

  executeCommand: async (command: string) => {
    const id = makeId()
    const entry: CommandHistoryEntry = {
      id,
      command,
      result: null,
      timestamp: new Date().toISOString(),
      status: "pending",
    }

    // Classify first
    try {
      const classification = await apiClassifyCommand(command)

      // If requires approval (tier 3+), show approval dialog
      if (classification.requires_approval) {
        set((s) => ({
          history: [...s.history, { ...entry, status: "pending" }],
          pendingApproval: { id, command, classification },
        }))
        return
      }
    } catch {
      // Classification failed — proceed with execution (backend will gate)
    }

    // No approval needed — execute directly
    set((s) => ({
      history: [...s.history, { ...entry, status: "running" }],
      isRunning: true,
      error: null,
    }))

    try {
      const result = await apiExecuteShell(command)

      set((s) => ({
        history: s.history.map((h) =>
          h.id === id
            ? { ...h, result, status: result.exit_code === 0 ? "success" : "error" }
            : h,
        ),
        currentDir: result.working_directory || s.currentDir,
        isRunning: false,
      }))
    } catch (err) {
      set((s) => ({
        history: s.history.map((h) =>
          h.id === id ? { ...h, status: "error" } : h,
        ),
        isRunning: false,
        error: (err as Error).message,
      }))
    }
  },

  approveAndRun: async () => {
    const { pendingApproval } = get()
    if (!pendingApproval) return

    const { id, command } = pendingApproval

    set((s) => ({
      history: s.history.map((h) =>
        h.id === id ? { ...h, status: "running" } : h,
      ),
      pendingApproval: null,
      isRunning: true,
      error: null,
    }))

    try {
      const result = await apiExecuteShell(command)

      set((s) => ({
        history: s.history.map((h) =>
          h.id === id
            ? { ...h, result, status: result.exit_code === 0 ? "success" : "error" }
            : h,
        ),
        currentDir: result.working_directory || s.currentDir,
        isRunning: false,
      }))
    } catch (err) {
      set((s) => ({
        history: s.history.map((h) =>
          h.id === id ? { ...h, status: "error" } : h,
        ),
        isRunning: false,
        error: (err as Error).message,
      }))
    }
  },

  rejectPending: () => {
    const { pendingApproval } = get()
    if (!pendingApproval) return

    set((s) => ({
      history: s.history.map((h) =>
        h.id === pendingApproval.id ? { ...h, status: "rejected" } : h,
      ),
      pendingApproval: null,
    }))
  },

  clearHistory: () => set({ history: [], error: null }),
}))
