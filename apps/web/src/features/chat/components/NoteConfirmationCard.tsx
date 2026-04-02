/**
 * NoteConfirmationCard — Inline card rendered in the chat when a note
 * operation requires user confirmation (HITL interrupt).
 *
 * Shown for destructive operations (delete, full-rewrite) when the
 * agent is running in SAFE or STRICT interaction mode.
 *
 * On action, calls POST /api/note-confirm which streams the response
 * back using the data-stream protocol.
 */

'use client'

import React, { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/shared/lib/utils'
import {
  Trash2,
  RefreshCw,
  Check,
  X,
  Loader2,
  FileText,
} from 'lucide-react'
import {
  useNoteConfirmationStore,
  type NoteConfirmationRequest,
} from '@/shared/store/note-confirmation-store'
import { useSidebarStore } from '@/features/chat/store'
import { useNoteStore } from '@/features/notes/store'

/* ═══════════════════════════════════════════════════════════════════
 * Action-specific config
 * ═══════════════════════════════════════════════════════════════════ */

const ACTION_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; Icon: typeof Trash2 }
> = {
  create: {
    label: 'Create Note',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    Icon: FileText,
  },
  delete: {
    label: 'Delete Note',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    Icon: Trash2,
  },
  update: {
    label: 'Full Rewrite',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    Icon: RefreshCw,
  },
}

/* ═══════════════════════════════════════════════════════════════════
 * Button helper
 * ═══════════════════════════════════════════════════════════════════ */

function ActionButton({
  onClick,
  disabled,
  loading,
  variant,
  icon,
  children,
}: {
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  variant: 'primary' | 'danger' | 'ghost'
  icon?: React.ReactNode
  children: React.ReactNode
}) {
  const styles = {
    primary: 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500/50',
    danger: 'bg-red-600 hover:bg-red-500 text-white border-red-500/50',
    ghost: 'bg-muted/30 hover:bg-muted/50 text-muted-foreground border-border/50',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium',
        'transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none',
        styles[variant],
      )}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {children}
    </button>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * Main component
 * ═══════════════════════════════════════════════════════════════════ */

export function NoteConfirmationCard() {
  const pending = useNoteConfirmationStore((s) => s.pending)
  const threadId = useNoteConfirmationStore((s) => s.threadId)
  const isResuming = useNoteConfirmationStore((s) => s.isResuming)
  const setResuming = useNoteConfirmationStore((s) => s.setResuming)
  const clearConfirmation = useNoteConfirmationStore((s) => s.clear)

  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleAction = useCallback(
    async (decision: 'approve' | 'reject') => {
      if (!pending || !threadId) return

      setResuming(true)
      setResult(null)

      try {
        const res = await fetch('/api/note-confirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            decision,
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
            } catch { /* skip */ }
          } else if (line.startsWith('2:')) {
            try {
              const data = JSON.parse(line.slice(2)) as unknown[]
              for (const item of data) {
                if (!item || typeof item !== 'object' || !('type' in item)) continue
                const evt = item as Record<string, unknown>

                // If a new note_confirmation_request comes in, set as pending
                if (evt.type === 'note_confirmation_request') {
                  useNoteConfirmationStore.getState().setPending(
                    {
                      confirmation_type: (evt.confirmation_type as string) ?? '',
                      note_id: (evt.note_id as string) ?? '',
                      note_title: (evt.note_title as string) ?? '',
                      action: (evt.action as string) ?? 'delete',
                      update_type: (evt.update_type as string) ?? null,
                      message: (evt.message as string) ?? '',
                      options: (evt.options as string[]) ?? ['approve', 'reject'],
                    },
                    threadId,
                  )
                  return
                }

                // Handle note_result events for sidebar updates
                if (evt.type === 'note_result') {
                  const noteAction = (evt.action as string) ?? ''
                  const ids = Array.isArray(evt.persisted_ids) ? evt.persisted_ids : []
                  if (noteAction === 'delete') {
                    for (const nid of ids) {
                      if (nid) {
                        useSidebarStore.getState().removeStickyNoteByDbId(String(nid))
                        useNoteStore.getState().removeNote(String(nid))
                      }
                    }
                  }
                }

                // Dispatch worker results to sidebar
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

        if (decision === 'reject') {
          setResult({ success: true, message: 'Operation cancelled.' })
        } else {
          const actionMsg = pending.action === 'delete'
            ? `Note "${pending.note_title}" deleted.`
            : pending.action === 'create'
              ? `Note "${pending.note_title}" created.`
              : `Note "${pending.note_title}" updated.`
          setResult({ success: true, message: actionMsg })
        }

        // Clear the pending confirmation (unless a new one was set)
        if (useNoteConfirmationStore.getState().pending?.note_id === pending.note_id) {
          clearConfirmation()
        }
      } catch (err) {
        setResult({ success: false, message: String(err) })
      } finally {
        setResuming(false)
      }
    },
    [pending, threadId, setResuming, clearConfirmation],
  )

  if (!pending) return null

  const actionCfg = ACTION_CONFIG[pending.action] ?? ACTION_CONFIG.delete
  const { Icon: ActionIcon } = actionCfg

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={cn(
        'mx-auto max-w-5xl rounded-xl border p-5 shadow-md',
        'bg-[var(--msg-assistant-bg)] backdrop-blur-xl',
        actionCfg.border,
      )}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-3 mb-4">
        <ActionIcon size={18} className={actionCfg.color} />
        <span className="font-bold text-sm tracking-tight text-foreground">
          {actionCfg.label} Confirmation
        </span>
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider',
            actionCfg.color,
            actionCfg.bg,
            actionCfg.border,
          )}
        >
          <ActionIcon size={12} />
          {pending.action.toUpperCase()}
        </span>
      </div>

      {/* ── Note info ── */}
      <div className="flex items-center gap-2 mb-3">
        <FileText size={14} className="text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">
          {pending.note_title || pending.note_id}
        </span>
      </div>

      {/* ── Message ── */}
      {pending.message && (
        <p className="text-xs text-muted-foreground mb-4">
          {pending.message}
        </p>
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
          <ActionButton
            onClick={() => handleAction('approve')}
            disabled={isResuming}
            loading={isResuming}
            variant={pending.action === 'delete' ? 'danger' : 'primary'}
            icon={<Check size={14} />}
          >
            {pending.action === 'delete' ? 'Delete' : pending.action === 'create' ? 'Create' : 'Proceed'}
          </ActionButton>
          <ActionButton
            onClick={() => handleAction('reject')}
            disabled={isResuming}
            variant="ghost"
            icon={<X size={14} />}
          >
            Cancel
          </ActionButton>
        </div>
      )}
    </motion.div>
  )
}
