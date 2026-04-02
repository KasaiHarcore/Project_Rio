/**
 * SQLApprovalCard — Inline card rendered in the chat when a SQL
 * operation requires user approval (HITL interrupt).
 *
 * Displays the generated SQL, classification info, and action buttons
 * (Approve, Always Approve, Reject, Edit & Approve).
 *
 * On action, calls POST /api/sql-approve which streams the response
 * back using the data-stream protocol.
 */

'use client'

import React, { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/shared/lib/utils'
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Check,
  X,
  Pencil,
  Loader2,
  AlertTriangle,
  Database,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useSQLApprovalStore, type SQLApprovalRequest } from '@/shared/store/sql-approval-store'
import { useSidebarStore } from '@/features/chat/store'

/* ═══════════════════════════════════════════════════════════════════
 * Danger-level badge styles
 * ═══════════════════════════════════════════════════════════════════ */

const DANGER_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; Icon: typeof Shield }
> = {
  safe: {
    label: 'SAFE',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    Icon: ShieldCheck,
  },
  low: {
    label: 'LOW',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    Icon: Shield,
  },
  medium: {
    label: 'MEDIUM',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    Icon: ShieldAlert,
  },
  high: {
    label: 'HIGH',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    Icon: ShieldAlert,
  },
  critical: {
    label: 'CRITICAL',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    Icon: ShieldAlert,
  },
}

/* ═══════════════════════════════════════════════════════════════════
 * Helpers
 * ═══════════════════════════════════════════════════════════════════ */

function DangerBadge({ level }: { level: string }) {
  const cfg = DANGER_CONFIG[level] ?? DANGER_CONFIG.medium
  const { Icon } = cfg
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider',
        cfg.color,
        cfg.bg,
        cfg.border,
      )}
    >
      <Icon size={12} />
      {cfg.label}
    </span>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * Main component
 * ═══════════════════════════════════════════════════════════════════ */

interface SQLApprovalCardProps {
  /** Append streamed text from the resume response into the chat. */
  onStreamText?: (text: string) => void
}

export function SQLApprovalCard({ onStreamText }: SQLApprovalCardProps) {
  const pending = useSQLApprovalStore((s) => s.pending)
  const threadId = useSQLApprovalStore((s) => s.threadId)
  const isResuming = useSQLApprovalStore((s) => s.isResuming)
  const setResuming = useSQLApprovalStore((s) => s.setResuming)
  const clearApproval = useSQLApprovalStore((s) => s.clear)

  const [isEditing, setIsEditing] = useState(false)
  const [editedSQL, setEditedSQL] = useState('')
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)
  const [showWarnings, setShowWarnings] = useState(false)

  const handleAction = useCallback(
    async (action: 'approve' | 'reject' | 'edit' | 'always_approve') => {
      if (!pending || !threadId) return

      // For edit action, enter edit mode first
      if (action === 'edit' && !isEditing) {
        setIsEditing(true)
        setEditedSQL(pending.sql)
        return
      }

      setResuming(true)
      setResult(null)

      try {
        const res = await fetch('/api/sql-approve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            action: action === 'edit' ? 'edit' : action,
            edited_sql: action === 'edit' ? editedSQL : undefined,
          }),
        })

        if (!res.ok) {
          const errText = await res.text()
          setResult({ success: false, message: errText || 'Request failed' })
          setResuming(false)
          return
        }

        // Read the streaming response and dispatch events
        const reader = res.body?.getReader()
        if (!reader) {
          setResult({ success: false, message: 'No response body' })
          setResuming(false)
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''
        const textParts: string[] = []

        const processLine = (line: string) => {
          if (line.startsWith('0:')) {
            try {
              const text = JSON.parse(line.slice(2)) as string
              textParts.push(text)
              onStreamText?.(text)
            } catch { /* skip */ }
          } else if (line.startsWith('2:')) {
            try {
              const data = JSON.parse(line.slice(2)) as unknown[]
              for (const item of data) {
                if (!item || typeof item !== 'object' || !('type' in item)) continue
                const evt = item as Record<string, unknown>

                // If a new sql_approval_request comes in (re-approval after retry),
                // set it as the new pending approval
                if (evt.type === 'sql_approval_request') {
                  useSQLApprovalStore.getState().setPending(
                    {
                      request_id: (evt.request_id as string) ?? '',
                      sql: (evt.sql as string) ?? '',
                      natural_query: (evt.natural_query as string) ?? '',
                      operation_type: (evt.operation_type as string) ?? '',
                      danger_level: (evt.danger_level as string) ?? '',
                      affected_tables: (evt.affected_tables as string[]) ?? [],
                      estimated_rows_affected: evt.estimated_rows_affected as string | null,
                      warnings: (evt.warnings as string[]) ?? [],
                      explanation: (evt.explanation as string) ?? '',
                      message: (evt.message as string) ?? '',
                    },
                    threadId,
                  )
                  return // exit early — new approval card will render
                }

                // Dispatch other events to sidebar
                if (evt.type === 'worker_result') {
                  useSidebarStore.getState().addLogicEntry({
                    title: evt.success ? `${evt.worker} completed` : `${evt.worker} failed`,
                    detail: (evt.content_preview as string) || undefined,
                    kind: 'tool-call',
                  })
                }
              }
            } catch { /* skip */ }
          } else if (line.startsWith('e:')) {
            try {
              const err = JSON.parse(line.slice(2)) as Record<string, string>
              setResult({ success: false, message: err.message || 'Error' })
            } catch { /* skip */ }
          }
        }

        // Stream read loop
        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            if (buffer.trim()) processLine(buffer)
            break
          }
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) {
            if (line.length > 0) processLine(line)
          }
        }

        if (action === 'reject') {
          setResult({ success: true, message: 'Operation cancelled.' })
        } else {
          setResult({
            success: true,
            message: textParts.length > 0 ? 'SQL executed successfully.' : 'Done.',
          })
        }

        // Clear the pending approval (unless a new one was set by re-approval)
        if (useSQLApprovalStore.getState().pending?.request_id === pending.request_id) {
          clearApproval()
        }
      } catch (err) {
        setResult({ success: false, message: String(err) })
      } finally {
        setResuming(false)
        setIsEditing(false)
      }
    },
    [pending, threadId, isEditing, editedSQL, setResuming, clearApproval, onStreamText],
  )

  if (!pending) return null

  const dangerCfg = DANGER_CONFIG[pending.danger_level] ?? DANGER_CONFIG.medium

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={cn(
        'mx-auto max-w-5xl rounded-xl border p-5 shadow-md',
        'bg-[var(--msg-assistant-bg)] backdrop-blur-xl',
        dangerCfg.border,
      )}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-3 mb-4">
        <Database size={18} className={dangerCfg.color} />
        <span className="font-bold text-sm tracking-tight text-foreground">
          SQL Approval Required
        </span>
        <DangerBadge level={pending.danger_level} />
        <span className="ml-auto text-xs text-muted-foreground font-mono uppercase">
          {pending.operation_type}
        </span>
      </div>

      {/* ── Natural language query ── */}
      {pending.natural_query && (
        <p className="text-xs text-muted-foreground mb-3 italic">
          &ldquo;{pending.natural_query}&rdquo;
        </p>
      )}

      {/* ── SQL display ── */}
      <div className="relative mb-4">
        {isEditing ? (
          <textarea
            className={cn(
              'w-full min-h-[120px] rounded-lg border p-3 font-mono text-xs',
              'bg-background/60 text-foreground border-border',
              'focus:outline-none focus:ring-1 focus:ring-primary/40',
            )}
            value={editedSQL}
            onChange={(e) => setEditedSQL(e.target.value)}
            spellCheck={false}
          />
        ) : (
          <pre
            className={cn(
              'rounded-lg border p-3 text-xs font-mono overflow-x-auto',
              'bg-background/40 text-foreground/90 border-border/50',
            )}
          >
            <code>{pending.sql}</code>
          </pre>
        )}
      </div>

      {/* ── Affected tables ── */}
      {pending.affected_tables.length > 0 && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
            Tables:
          </span>
          {pending.affected_tables.map((t) => (
            <span
              key={t}
              className="rounded-md bg-muted/40 px-2 py-0.5 text-[10px] font-mono text-muted-foreground border border-border/30"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      {/* ── Warnings (collapsible) ── */}
      {pending.warnings.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowWarnings(!showWarnings)}
            className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 transition-colors"
          >
            <AlertTriangle size={12} />
            <span className="font-medium">{pending.warnings.length} warning(s)</span>
            {showWarnings ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showWarnings && (
            <ul className="mt-2 space-y-1 pl-5">
              {pending.warnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-400/80 list-disc">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Explanation ── */}
      {pending.explanation && (
        <p className="text-xs text-muted-foreground mb-4">{pending.explanation}</p>
      )}

      {/* ── Result display ── */}
      {result && (
        <div
          className={cn(
            'rounded-lg border p-3 mb-4 text-xs',
            result.success
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400',
          )}
        >
          {result.message}
        </div>
      )}

      {/* ── Action buttons ── */}
      {!result && (
        <div className="flex items-center gap-2 flex-wrap">
          {isEditing ? (
            <>
              <ActionButton
                onClick={() => handleAction('edit')}
                disabled={isResuming || !editedSQL.trim()}
                loading={isResuming}
                variant="primary"
                icon={<Check size={14} />}
              >
                Execute Edited SQL
              </ActionButton>
              <ActionButton
                onClick={() => {
                  setIsEditing(false)
                  setEditedSQL('')
                }}
                disabled={isResuming}
                variant="ghost"
                icon={<X size={14} />}
              >
                Cancel Edit
              </ActionButton>
            </>
          ) : (
            <>
              <ActionButton
                onClick={() => handleAction('approve')}
                disabled={isResuming}
                loading={isResuming}
                variant="primary"
                icon={<Check size={14} />}
              >
                Approve
              </ActionButton>
              <ActionButton
                onClick={() => handleAction('always_approve')}
                disabled={isResuming}
                variant="secondary"
                icon={<ShieldCheck size={14} />}
              >
                Always Approve
              </ActionButton>
              <ActionButton
                onClick={() => handleAction('edit')}
                disabled={isResuming}
                variant="secondary"
                icon={<Pencil size={14} />}
              >
                Edit SQL
              </ActionButton>
              <ActionButton
                onClick={() => handleAction('reject')}
                disabled={isResuming}
                variant="destructive"
                icon={<X size={14} />}
              >
                Reject
              </ActionButton>
            </>
          )}
        </div>
      )}
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * ActionButton — Styled button for the approval card
 * ═══════════════════════════════════════════════════════════════════ */

function ActionButton({
  children,
  onClick,
  disabled,
  loading,
  variant,
  icon,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  variant: 'primary' | 'secondary' | 'destructive' | 'ghost'
  icon?: React.ReactNode
}) {
  const variantStyles: Record<string, string> = {
    primary:
      'bg-primary/90 text-primary-foreground hover:bg-primary border-primary/60',
    secondary:
      'bg-muted/40 text-foreground hover:bg-muted/60 border-border/50',
    destructive:
      'bg-red-500/10 text-red-400 hover:bg-red-500/20 border-red-500/30',
    ghost:
      'bg-transparent text-muted-foreground hover:bg-muted/30 border-transparent',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5',
        'text-xs font-medium transition-all duration-200',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantStyles[variant],
      )}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {children}
    </button>
  )
}
