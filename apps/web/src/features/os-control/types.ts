/* ─── OS Control Types ────────────────────────────────────────────── */

export type RiskTier = 1 | 2 | 3 | 4 | 5

export const RISK_TIER_LABELS: Record<RiskTier, string> = {
  1: "None",
  2: "Soft Confirm",
  3: "Hard Confirm",
  4: "Explicit Approve",
  5: "Destructive",
}

export const RISK_TIER_COLORS: Record<RiskTier, string> = {
  1: "text-green-400",
  2: "text-blue-400",
  3: "text-yellow-400",
  4: "text-orange-400",
  5: "text-red-500",
}

export const RISK_TIER_BG: Record<RiskTier, string> = {
  1: "bg-green-500/10",
  2: "bg-blue-500/10",
  3: "bg-yellow-500/10",
  4: "bg-orange-500/10",
  5: "bg-red-500/10",
}

export interface ShellResult {
  command: string
  exit_code: number
  stdout: string
  stderr: string
  execution_time_ms: number
  timed_out: boolean
  working_directory: string
  risk_tier: RiskTier
}

export interface ShellClassifyResult {
  command: string
  risk_tier: RiskTier
  risk_label: string
  requires_approval: boolean
}

export interface CommandHistoryEntry {
  id: string
  command: string
  result: ShellResult | null
  timestamp: string
  status: "pending" | "running" | "success" | "error" | "approved" | "rejected"
}
