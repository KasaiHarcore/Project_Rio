"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { BentoCard } from "@/components/ui/bento-card"
import { useOSControlStore } from "@/features/os-control/store"
import { useUIStore } from "@/shared/store/ui-store"
import {
  RISK_TIER_LABELS,
  RISK_TIER_COLORS,
  RISK_TIER_BG,
  type RiskTier,
} from "@/features/os-control/types"
import {
  Terminal,
  Send,
  Trash2,
  ShieldAlert,
  ShieldCheck,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  ChevronRight,
  MonitorSmartphone,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/shared/lib/utils"

export function OSControlView() {
  const userRole = useUIStore((s) => s.userRole)

  if (userRole !== "admin") {
    return (
      <DashboardLayout>
        <PageTransition>
          <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
            <div className="p-4 rounded-2xl bg-red-500/10">
              <ShieldAlert className="w-12 h-12 text-red-400" />
            </div>
            <h2 className="text-xl font-bold">Access Restricted</h2>
            <p className="text-sm text-muted-foreground text-center max-w-md">
              OS Control is restricted to admin users only. Contact your
              administrator if you need shell, browser, or GUI access.
            </p>
          </div>
        </PageTransition>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <PageTransition>
        <div className="flex flex-col h-full p-6 gap-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/10">
                <MonitorSmartphone className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">OS Control</h1>
                <p className="text-xs text-muted-foreground">
                  Shell execution &middot; Risk-tiered &middot; Admin only
                </p>
              </div>
            </div>
            <RiskLegend />
          </div>

          {/* Terminal area */}
          <TerminalPanel />
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}

/* ─── Risk Legend ────────────────────────────────────────────────── */

function RiskLegend() {
  return (
    <div className="hidden md:flex items-center gap-2">
      {([1, 2, 3, 4, 5] as RiskTier[]).map((tier) => (
        <span
          key={tier}
          className={cn(
            "px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider",
            RISK_TIER_BG[tier],
            RISK_TIER_COLORS[tier],
          )}
        >
          T{tier}
        </span>
      ))}
    </div>
  )
}

/* ─── Terminal Panel ────────────────────────────────────────────── */

function TerminalPanel() {
  const history = useOSControlStore((s) => s.history)
  const currentDir = useOSControlStore((s) => s.currentDir)
  const isRunning = useOSControlStore((s) => s.isRunning)
  const pendingApproval = useOSControlStore((s) => s.pendingApproval)
  const error = useOSControlStore((s) => s.error)
  const executeCommand = useOSControlStore((s) => s.executeCommand)
  const approveAndRun = useOSControlStore((s) => s.approveAndRun)
  const rejectPending = useOSControlStore((s) => s.rejectPending)
  const clearHistory = useOSControlStore((s) => s.clearHistory)

  const [input, setInput] = React.useState("")
  const [historyIndex, setHistoryIndex] = React.useState(-1)
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  // Auto-scroll on new output
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [history, pendingApproval])

  // Focus input on mount
  React.useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const cmd = input.trim()
    if (!cmd || isRunning) return
    setInput("")
    setHistoryIndex(-1)
    executeCommand(cmd)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const commands = history.map((h) => h.command)
    if (e.key === "ArrowUp") {
      e.preventDefault()
      const nextIdx = Math.min(historyIndex + 1, commands.length - 1)
      setHistoryIndex(nextIdx)
      setInput(commands[commands.length - 1 - nextIdx] ?? "")
    } else if (e.key === "ArrowDown") {
      e.preventDefault()
      const nextIdx = Math.max(historyIndex - 1, -1)
      setHistoryIndex(nextIdx)
      setInput(nextIdx < 0 ? "" : commands[commands.length - 1 - nextIdx] ?? "")
    }
  }

  return (
    <BentoCard className="flex-1 flex flex-col overflow-hidden p-0 min-h-0">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card/50">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-green-400" />
          <span className="text-xs font-mono text-muted-foreground">
            {currentDir}
          </span>
        </div>
        <button
          onClick={clearHistory}
          className="px-2 py-1 rounded text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors flex items-center gap-1"
        >
          <Trash2 className="w-3 h-3" />
          Clear
        </button>
      </div>

      {/* Output area */}
      <div
        ref={scrollRef}
        onClick={() => inputRef.current?.focus()}
        className="flex-1 overflow-y-auto custom-scrollbar p-4 font-mono text-sm space-y-3 bg-[var(--page-bg)]"
      >
        {history.length === 0 && !pendingApproval && (
          <div className="text-muted-foreground text-xs">
            <p>Welcome to OS Control terminal.</p>
            <p className="mt-1 opacity-60">
              Type a command below. Risk tier is auto-classified.
              Tier 3+ requires approval before execution.
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {history.map((entry) => (
            <CommandEntry key={entry.id} entry={entry} />
          ))}
        </AnimatePresence>

        {/* Approval dialog */}
        {pendingApproval && (
          <ApprovalDialog
            command={pendingApproval.command}
            riskTier={pendingApproval.classification.risk_tier}
            riskLabel={pendingApproval.classification.risk_label}
            onApprove={approveAndRun}
            onReject={rejectPending}
          />
        )}

        {/* Global error */}
        {error && (
          <div className="flex items-start gap-2 text-red-400 text-xs">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Input line */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-4 py-3 border-t border-border bg-card/50"
      >
        <ChevronRight className="w-4 h-4 text-green-400 shrink-0" />
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
          placeholder={isRunning ? "Running..." : "Enter command..."}
          autoComplete="off"
          spellCheck={false}
          className="flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
        />
        <button
          type="submit"
          disabled={isRunning || !input.trim()}
          className="p-2 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>
    </BentoCard>
  )
}

/* ─── Command Entry ─────────────────────────────────────────────── */

function CommandEntry({ entry }: { entry: import("../types").CommandHistoryEntry }) {
  const { command, result, status } = entry

  const statusIcon = {
    pending: <Clock className="w-3 h-3 text-muted-foreground" />,
    running: <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />,
    success: <CheckCircle2 className="w-3 h-3 text-green-400" />,
    error: <XCircle className="w-3 h-3 text-red-400" />,
    approved: <ShieldCheck className="w-3 h-3 text-green-400" />,
    rejected: <ShieldAlert className="w-3 h-3 text-red-400" />,
  }[status]

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="space-y-1"
    >
      {/* Command line */}
      <div className="flex items-center gap-2">
        {statusIcon}
        <span className="text-green-400 font-mono text-xs">$</span>
        <span className="text-foreground font-mono text-xs">{command}</span>
        {result && (
          <span
            className={cn(
              "ml-auto px-1.5 py-0.5 rounded text-[10px] font-bold",
              RISK_TIER_BG[result.risk_tier as RiskTier],
              RISK_TIER_COLORS[result.risk_tier as RiskTier],
            )}
          >
            T{result.risk_tier}
          </span>
        )}
      </div>

      {/* Output */}
      {result?.stdout && (
        <pre className="text-xs text-foreground/80 whitespace-pre-wrap pl-5 max-h-60 overflow-y-auto custom-scrollbar">
          {result.stdout}
        </pre>
      )}

      {/* Stderr */}
      {result?.stderr && (
        <pre className="text-xs text-red-400/80 whitespace-pre-wrap pl-5 max-h-40 overflow-y-auto custom-scrollbar">
          {result.stderr}
        </pre>
      )}

      {/* Timing */}
      {result && (
        <div className="flex items-center gap-3 pl-5 text-[10px] text-muted-foreground">
          <span>exit: {result.exit_code}</span>
          <span>{result.execution_time_ms}ms</span>
          {result.timed_out && (
            <span className="text-yellow-400">timed out</span>
          )}
        </div>
      )}

      {/* Rejected */}
      {status === "rejected" && (
        <div className="text-xs text-red-400/60 pl-5 italic">
          Command rejected — not executed.
        </div>
      )}
    </motion.div>
  )
}

/* ─── Approval Dialog ───────────────────────────────────────────── */

function ApprovalDialog({
  command,
  riskTier,
  riskLabel,
  onApprove,
  onReject,
}: {
  command: string
  riskTier: RiskTier
  riskLabel: string
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "rounded-xl border p-4 space-y-3",
        RISK_TIER_BG[riskTier],
        "border-current/20",
      )}
    >
      <div className="flex items-center gap-2">
        <ShieldAlert className={cn("w-5 h-5", RISK_TIER_COLORS[riskTier])} />
        <span className={cn("text-sm font-bold", RISK_TIER_COLORS[riskTier])}>
          {riskLabel} — Approval Required
        </span>
      </div>

      <div className="bg-black/20 rounded-lg p-3">
        <code className="text-xs font-mono text-foreground">{command}</code>
      </div>

      <p className="text-xs text-muted-foreground">
        This command has been classified as{" "}
        <strong className={RISK_TIER_COLORS[riskTier]}>
          Tier {riskTier}
        </strong>
        . Do you want to proceed?
      </p>

      <div className="flex items-center gap-2">
        <button
          onClick={onApprove}
          className="px-4 py-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors text-xs font-bold flex items-center gap-2"
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          Approve & Run
        </button>
        <button
          onClick={onReject}
          className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-xs font-bold flex items-center gap-2"
        >
          <XCircle className="w-3.5 h-3.5" />
          Reject
        </button>
      </div>
    </motion.div>
  )
}
