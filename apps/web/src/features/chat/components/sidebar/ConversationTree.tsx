"use client"

import React, { useEffect, useRef } from 'react'
import { cn } from '@/shared/lib/utils'
import {
  User as UserIcon, Bot, Brain, Route, Wrench,
  Loader2,
} from 'lucide-react'
import type { MessageExchange, ToolBranch } from './use-message-exchanges'

/* ─── Types ──────────────────────────────────────────────────────── */

interface ConversationTreeProps {
  exchanges: MessageExchange[]
  onSelectExchange: (exchange: MessageExchange) => void
  /** Whether the last exchange is still streaming */
  isStreaming?: boolean
}

/* ─── Helpers ────────────────────────────────────────────────────── */

function truncate(text: string, max: number): string {
  if (!text) return ''
  const clean = text.replace(/\n/g, ' ').trim()
  return clean.length > max ? clean.slice(0, max) + '…' : clean
}

function formatTime(ts: number): string {
  if (!ts || ts === Infinity) return ''
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getMsgText(msg: import('ai').UIMessage | null): string {
  if (!msg) return ''
  const text = msg.parts
    ?.filter((p: any) => p.type === 'text')
    .map((p: any) => p.text)
    .join('') || (msg as any).content || ''
  return text
}

/* ═══════════════════════════════════════════════════════════════════
   ConversationTree
   ═══════════════════════════════════════════════════════════════════ */

export function ConversationTree({ exchanges, onSelectExchange, isStreaming }: ConversationTreeProps) {
  const endRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest node
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [exchanges.length])

  if (exchanges.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-4 text-center border-[var(--chat-sidebar-artifact-border)]">
        <Bot className="h-5 w-5 mx-auto mb-1.5 text-[var(--chat-sidebar-stat-label)]" />
        <p className="text-[9px] text-[var(--chat-sidebar-stat-label)]">
          Conversation flow appears here
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {exchanges.map((ex, idx) => (
        <React.Fragment key={ex.id}>
          {/* Connector line above (skip first) */}
          {idx > 0 && <ConnectorLine />}

          {/* Exchange node */}
          <ExchangeNode
            exchange={ex}
            onClick={() => onSelectExchange(ex)}
            isLast={idx === exchanges.length - 1}
            isStreaming={isStreaming && idx === exchanges.length - 1}
          />
        </React.Fragment>
      ))}

      {/* Streaming indicator at bottom */}
      {isStreaming && (
        <>
          <ConnectorLine pulsing />
          <div className="flex items-center justify-center py-1">
            <div className="flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin text-[var(--chat-sidebar-stat-text)]" />
              <span className="text-[8px] font-bold uppercase tracking-wider text-[var(--chat-sidebar-stat-text)]">
                Processing
              </span>
            </div>
          </div>
        </>
      )}

      <div ref={endRef} />
    </div>
  )
}

/* ─── ConnectorLine ─────────────────────────────────────────────── */

function ConnectorLine({ pulsing }: { pulsing?: boolean }) {
  return (
    <div className="flex justify-center py-0.5">
      <div
        className={cn(
          "w-0.5 h-4 rounded-full",
          pulsing
            ? "bg-[var(--chat-sidebar-stat-text)] animate-pulse"
            : "bg-[var(--chat-sidebar-artifact-line)]"
        )}
      />
    </div>
  )
}

/* ─── ExchangeNode ──────────────────────────────────────────────── */

interface ExchangeNodeProps {
  exchange: MessageExchange
  onClick: () => void
  isLast: boolean
  isStreaming?: boolean
}

function ExchangeNode({ exchange, onClick, isLast, isStreaming }: ExchangeNodeProps) {
  const { userMessage, assistantMessage, logicEntries, toolBranches, thinkingEntries } = exchange
  const userText = getMsgText(userMessage)
  const assistantText = getMsgText(assistantMessage)
  const totalSteps = logicEntries.length

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-xl border p-2.5 transition-all",
        "bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)]",
        "hover:border-[var(--chat-sidebar-artifact-hover-border)] hover:bg-[var(--chat-sidebar-artifact-hover-bg)]",
        "focus:outline-none focus:ring-1 focus:ring-[var(--chat-sidebar-stat-text)]/30",
      )}
    >
      {/* User message row */}
      {userMessage && (
        <div className="flex items-center gap-1.5 mb-1">
          <UserIcon className="h-3 w-3 text-sky-400 flex-shrink-0" />
          <span className="text-[8px] font-bold text-sky-400 uppercase tracking-wider flex-shrink-0">You</span>
          <span className="text-[9px] text-[var(--chat-sidebar-value)] truncate flex-1 min-w-0">
            {truncate(userText, 35)}
          </span>
        </div>
      )}

      {/* Tool branches visualization */}
      {toolBranches.length > 0 && (
        <ToolBranchesViz branches={toolBranches} />
      )}

      {/* Assistant message row */}
      {assistantMessage && (
        <div className="flex items-center gap-1.5 mb-1">
          <Bot className="h-3 w-3 text-[var(--chat-sidebar-stat-text)] flex-shrink-0" />
          <span className="text-[8px] font-bold text-[var(--chat-sidebar-stat-text)] uppercase tracking-wider flex-shrink-0">Rio</span>
          <span className="text-[9px] text-[var(--chat-sidebar-stat-label)] truncate flex-1 min-w-0">
            {isStreaming && isLast ? 'Responding…' : truncate(assistantText, 35)}
          </span>
        </div>
      )}

      {/* Footer: timestamp + logic step count */}
      <div className="flex items-center justify-between mt-1">
        <span className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/60">
          {formatTime(exchange.timeStart)}
        </span>
        <div className="flex items-center gap-1.5">
          {thinkingEntries.length > 0 && (
            <span className="flex items-center gap-0.5 text-[7px] font-bold text-amber-400/70">
              <Brain className="h-2.5 w-2.5" />
              {thinkingEntries.length}
            </span>
          )}
          {totalSteps > 0 && (
            <span className="rounded-full px-1.5 py-0.5 text-[7px] font-bold bg-[var(--chat-sidebar-stat-text)]/20 text-[var(--chat-sidebar-stat-text)]">
              {totalSteps} {totalSteps === 1 ? 'step' : 'steps'}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

/* ─── ToolBranchesViz ───────────────────────────────────────────── */

function ToolBranchesViz({ branches }: { branches: ToolBranch[] }) {
  const isParallel = branches.length > 1

  return (
    <div className={cn("my-1 ml-3 pl-2 border-l-2", "border-[var(--chat-sidebar-artifact-line)]/40")}>
      {isParallel ? (
        // Multiple parallel branches shown side by side
        <div className="space-y-0.5">
          {branches.map((branch) => (
            <div key={branch.id} className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400/60 flex-shrink-0" />
              <Wrench className="h-2.5 w-2.5 text-violet-400/70 flex-shrink-0" />
              <span className="text-[8px] text-violet-400/70 truncate">
                {branch.entries.map((e) => e.title).join(', ')}
              </span>
              {branch.entries.length > 1 && (
                <span className="text-[7px] font-bold text-violet-400/50 flex-shrink-0">
                  ×{branch.entries.length}
                </span>
              )}
            </div>
          ))}
        </div>
      ) : branches.length === 1 ? (
        // Single branch — show stacked
        <div className="flex items-center gap-1.5">
          <Wrench className="h-2.5 w-2.5 text-violet-400/70 flex-shrink-0" />
          <span className="text-[8px] text-violet-400/70 truncate">
            {branches[0].entries[0].title}
          </span>
          {branches[0].entries.length > 1 && (
            <span className="text-[7px] font-bold text-violet-400/50 flex-shrink-0">
              +{branches[0].entries.length - 1} more
            </span>
          )}
        </div>
      ) : null}
    </div>
  )
}
