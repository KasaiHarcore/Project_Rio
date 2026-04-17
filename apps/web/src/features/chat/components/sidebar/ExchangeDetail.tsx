"use client"

import React from 'react'
import { cn } from '@/shared/lib/utils'
import {
  ChevronLeft, Brain, Route, Wrench, Info,
  User as UserIcon, Bot,
} from 'lucide-react'
import type { MessageExchange } from './use-message-exchanges'

/* ─── Icon / color maps (same as original Logic Feed) ──────────── */

const LOGIC_ICONS: Record<string, React.ComponentType<Record<string, unknown>>> = {
  thinking: Brain,
  decision: Route,
  'tool-call': Wrench,
  info: Info,
}

const LOGIC_COLORS: Record<string, string> = {
  thinking: 'text-amber-400',
  decision: 'text-emerald-400',
  'tool-call': 'text-violet-400',
  info: 'text-sky-400',
}

/* ─── Helpers ────────────────────────────────────────────────────── */

function truncate(text: string, max: number): string {
  if (!text) return ''
  const clean = text.replace(/\n/g, ' ').trim()
  return clean.length > max ? clean.slice(0, max) + '…' : clean
}

function getMsgText(msg: import('ai').UIMessage | null): string {
  if (!msg) return ''
  return msg.parts
    ?.filter((p: any) => p.type === 'text')
    .map((p: any) => p.text)
    .join('') || (msg as any).content || ''
}

/* ═══════════════════════════════════════════════════════════════════
   ExchangeDetail
   ═══════════════════════════════════════════════════════════════════ */

interface ExchangeDetailProps {
  exchange: MessageExchange
  onBack: () => void
}

export function ExchangeDetail({ exchange, onBack }: ExchangeDetailProps) {
  const { userMessage, assistantMessage, logicEntries } = exchange
  const sortedEntries = [...logicEntries].sort((a, b) => a.timestamp - b.timestamp)

  return (
    <div className="space-y-3">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)] transition-colors"
      >
        <ChevronLeft className="h-3 w-3" />
        Back to tree
      </button>

      {/* Exchange summary card */}
      <div className="rounded-xl border p-2.5 bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)]">
        {userMessage && (
          <div className="flex items-center gap-1.5 mb-1">
            <UserIcon className="h-3 w-3 text-sky-400 flex-shrink-0" />
            <span className="text-[8px] font-bold text-sky-400 uppercase tracking-wider flex-shrink-0">You</span>
            <span className="text-[9px] text-[var(--chat-sidebar-value)] truncate flex-1 min-w-0">
              {truncate(getMsgText(userMessage), 50)}
            </span>
          </div>
        )}
        {assistantMessage && (
          <div className="flex items-center gap-1.5">
            <Bot className="h-3 w-3 text-[var(--chat-sidebar-stat-text)] flex-shrink-0" />
            <span className="text-[8px] font-bold text-[var(--chat-sidebar-stat-text)] uppercase tracking-wider flex-shrink-0">Rio</span>
            <span className="text-[9px] text-[var(--chat-sidebar-stat-label)] truncate flex-1 min-w-0">
              {truncate(getMsgText(assistantMessage), 50)}
            </span>
          </div>
        )}
      </div>

      {/* Logic entries list */}
      {sortedEntries.length === 0 ? (
        <div className="rounded-xl border border-dashed p-3 text-center border-[var(--chat-sidebar-artifact-border)]">
          <Info className="h-4 w-4 mx-auto mb-1 text-[var(--chat-sidebar-stat-label)]" />
          <p className="text-[9px] text-[var(--chat-sidebar-stat-label)]">
            No thinking steps recorded for this exchange
          </p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {sortedEntries.map((entry) => {
            const Icon = LOGIC_ICONS[entry.kind] ?? Info
            const color = LOGIC_COLORS[entry.kind] ?? 'text-slate-400'
            return (
              <div
                key={entry.id}
                className="flex items-start gap-2 rounded-lg px-2.5 py-2 bg-[var(--chat-sidebar-artifact-bg)]/60 border border-[var(--chat-sidebar-artifact-border)]/50"
              >
                <Icon className={cn('h-3 w-3 mt-0.5 flex-shrink-0', color)} />
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold text-[var(--chat-sidebar-value)] leading-tight">
                    {entry.title}
                  </p>
                  {entry.detail && (
                    <p className="text-[8px] text-[var(--chat-sidebar-stat-label)] mt-0.5 leading-snug break-words">
                      {entry.detail}
                    </p>
                  )}
                  <p className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/60 mt-0.5">
                    {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
