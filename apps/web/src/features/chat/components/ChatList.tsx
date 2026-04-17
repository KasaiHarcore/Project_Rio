import React, { useEffect, useRef, useCallback, useState } from 'react'
import { UIMessage } from 'ai'
import { cn } from '@/shared/lib/utils'
import { User, ArrowRight, Target, Upload, RefreshCw, Pencil, ChevronLeft, ChevronRight, X, Check, Clock, Database, Globe, Code2, Wrench, ExternalLink } from 'lucide-react'
import type { MessageNode } from '@/features/chat/lib/message-tree'
import { findNode, getSiblings } from '@/features/chat/lib/message-tree'
import { useBranchStore } from '@/features/chat/stores/branch-store'
import { useSidebarStore, type LogicEntry } from '@/features/chat/store'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/shared/lib/agent-config'
import { SmartDataCard } from './SmartDataCard'
import { SQLApprovalCard } from './SQLApprovalCard'
import { NoteConfirmationCard } from './NoteConfirmationCard'
import { useSQLApprovalStore } from '@/features/chat/stores/sql-approval-store'
import { useNoteConfirmationStore } from '@/features/chat/stores/note-confirmation-store'
import { CHARACTERS, type CharacterId } from '@/features/rio/types'
import { TypingIndicator } from '@/components/ui/typing-indicator'
import { useEmotionalStore, type Mood } from '@/features/emotional/store'
import Image from 'next/image'
import { useRouter } from 'next/navigation'

/** Format a Date to a short local time string, e.g. "14:32" or "02:32 PM". */
function formatMessageTime(d?: Date | null): string {
  if (!d || isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface ChatListProps {
  messages: UIMessage[]
  isLoading?: boolean
  /** Chat status from useChat: ready | streaming | submitted | error */
  status?: 'ready' | 'streaming' | 'submitted' | 'error'
  /** Full message tree for branch navigation */
  messageTree?: MessageNode[]
  /** Callback to regenerate an assistant response for a user message */
  onRegenerate?: (userMessageId: string) => void
  /** Whether a regeneration is currently in progress */
  regenerating?: boolean
  /** Callback to edit a user message (creates a new sibling branch) */
  onEditMessage?: (messageId: string, newContent: string) => Promise<void> | void
  /** Whether an edit is currently in progress */
  editing?: boolean
  /** Message id whose carousel should pulse to draw attention (after edit) */
  pulseCarouselForId?: string | null
}

// ── Mood-Aware Greetings ────────────────────────────────────────────────
function getMoodGreeting(mood: Mood): string {
  const greetings: Record<Mood, string> = {
    happy: "Neural link ready!",
    excited: "Let's do this, Sensei!",
    neutral: "System online.",
    sad: "...I'm here if you need me.",
    frustrated: "Connection stable. Ready when you are.",
    tired: "Low power mode active..."
  }
  return greetings[mood] || "Neural link established."
}

export function ChatList({
  messages, isLoading, status, messageTree,
  onRegenerate, regenerating,
  onEditMessage, editing, pulseCarouselForId,
}: ChatListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { mood, fetchState } = useEmotionalStore()
  const router = useRouter()
  const { selectBranch, nextBranch, prevBranch, branchSelections } = useBranchStore()
  const logicEntries = useSidebarStore((s) => s.logicEntries)

  // Inline-edit state: only one user message can be in edit mode at a time.
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState('')

  const startEdit = useCallback((msg: UIMessage) => {
    const text = msg.parts
      ?.filter((p: any) => p.type === 'text')
      .map((p: any) => p.text)
      .join('') || (msg as any).content || ''
    setEditDraft(text)
    setEditingMessageId(msg.id)
  }, [])
  const cancelEdit = useCallback(() => {
    setEditingMessageId(null)
    setEditDraft('')
  }, [])
  const commitEdit = useCallback(async () => {
    if (!onEditMessage || !editingMessageId) return
    const trimmed = editDraft.trim()
    if (!trimmed) return
    const id = editingMessageId
    setEditingMessageId(null)
    setEditDraft('')
    await onEditMessage(id, trimmed)
  }, [onEditMessage, editingMessageId, editDraft])

  useEffect(() => {
    fetchState('rio')
  }, [fetchState])

  useEffect(() => {
    // Smooth scroll during streaming, instant jump otherwise
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({
        behavior: status === 'streaming' ? 'smooth' : 'auto',
        block: 'end',
      })
    }
  }, [messages, status])

  const greeting = getMoodGreeting(mood)

  // Empty state when no messages
  if (messages.length === 0) {
    return (
      <section ref={scrollRef} role="status" aria-label="Waiting for messages" className="flex-1 overflow-y-auto p-6 lg:p-12 flex items-center justify-center">
        <div className="text-center max-w-md">
          {/* Agent Avatar with Mood */}
          <div className="mx-auto mb-6 relative group w-fit">
            <div className="absolute inset-0 rounded-2xl blur-xl opacity-20 group-hover:opacity-40 transition-opacity bg-[var(--empty-glow)]"></div>
            <div className="relative w-32 h-32 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 p-2 shadow-[0_0_30px_rgba(79,70,229,0.3)]">
              <div className="w-full h-full rounded-xl bg-indigo-950 overflow-hidden relative">
                <Image
                  src="/images/avatar.png"
                  alt="Rio"
                  fill
                  className="object-contain"
                />
              </div>
            </div>
          </div>

          {/* Mood-Aware Welcome Text */}
          <h2 className="text-xl font-black mb-2 tracking-tight text-[var(--empty-title)]">
            {greeting}
          </h2>
          <p className="text-sm mb-8 font-medium leading-relaxed text-[var(--empty-text)]">
            System ready. Initialization complete.<br/>
            Waiting for direct command input...
          </p>

          {/* Quick Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 mt-8 mb-6">
            <button
              onClick={() => {
                const lastThreadId = localStorage.getItem('last-thread-id')
                if (lastThreadId) {
                  router.push(`/operation/${lastThreadId}`)
                } else {
                  router.push('/operation')
                }
              }}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <ArrowRight size={16} />
              Resume Last Chat
            </button>
            <button
              onClick={() => router.push('/mission?new=true')}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <Target size={16} />
              Start Mission
            </button>
            <button
              onClick={() => router.push('/knowledge')}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <Upload size={16} />
              Upload Document
            </button>
          </div>

          {/* Status Indicator */}
          <div
            className="inline-flex items-center gap-3 rounded-lg border px-4 py-2 shadow-sm transition-all hover:scale-105 backdrop-blur-sm bg-[var(--empty-indicator-bg)] border-[var(--empty-indicator-border)]"
            style={{ boxShadow: 'var(--empty-indicator-shadow)' }}
          >
            <div className="h-2 w-2 rounded-full animate-pulse bg-[var(--empty-dot)]" style={{ boxShadow: `0 0 8px var(--empty-dot-glow)` }}></div>
            <span className="font-mono text-[10px] font-bold uppercase text-[var(--empty-label-text)]">
                Awaiting Orders • {mood}
            </span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={scrollRef} role="log" aria-label="Chat messages" className="flex-1 overflow-y-auto overflow-x-hidden p-4 lg:p-8 space-y-6 scroll-smooth custom-scrollbar">
      {messages.map((m, idx) => {
        const isAssistant = m.role === 'assistant';
        const msgCharacterId = (m as any).character_id as CharacterId | undefined;
        const characterName = msgCharacterId
          ? CHARACTERS.find(c => c.id === msgCharacterId)?.name
          : undefined;

        // Show blinking cursor on the last assistant message while streaming
        const isLastAssistant = isAssistant && idx === messages.length - 1;
        const showStreamingCursor = isLastAssistant && status === 'streaming';

        return (
          <div key={m.id} className={cn("group mx-auto flex max-w-5xl items-start gap-4", !isAssistant && "flex-row-reverse")}>

            {/* Avatar Column */}
            <div className="flex flex-col items-center flex-shrink-0 mt-1 gap-1">
              {isAssistant ? (
                <>
                  <AgentMessageAvatar characterId={msgCharacterId} />
                  {characterName && (
                    <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-wider">{characterName}</span>
                  )}
                </>
              ) : (
                <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-colors bg-[var(--user-avatar-bg)] border-[var(--user-avatar-border)]">
                  <User className="h-5 w-5 text-[var(--user-avatar-icon)]" />
                </div>
              )}
            </div>

            {/* Content Column (Smart Card) */}
            <div className="flex-1 min-w-0 max-w-[85%]">
                {editingMessageId === m.id ? (
                  // Inline edit mode: textarea replaces the message bubble.
                  // Save creates a sibling branch via the edit endpoint.
                  <div className="rounded-2xl border border-rose-500/40 bg-[var(--user-avatar-bg)] p-3 space-y-2 shadow-[0_0_12px_rgba(244,63,94,0.25)]">
                    <textarea
                      autoFocus
                      value={editDraft}
                      onChange={(e) => setEditDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          cancelEdit()
                        } else if ((e.key === 'Enter' && (e.metaKey || e.ctrlKey))) {
                          e.preventDefault()
                          void commitEdit()
                        }
                      }}
                      rows={Math.min(10, Math.max(2, editDraft.split('\n').length))}
                      className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 outline-none resize-none"
                      placeholder="Edit your message..."
                      disabled={editing}
                    />
                    <div className="flex items-center justify-between gap-2 pt-1 border-t border-rose-500/20">
                      <span className="text-[9px] font-mono uppercase tracking-wider text-rose-300/70">
                        Editing → creates a new branch
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={cancelEdit}
                          disabled={editing}
                          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 hover:bg-white/5 disabled:opacity-40 transition-colors"
                        >
                          <X className="h-3 w-3" />
                          Cancel
                        </button>
                        <button
                          onClick={() => void commitEdit()}
                          disabled={editing || !editDraft.trim()}
                          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-black uppercase tracking-wider bg-rose-500/20 text-rose-200 hover:bg-rose-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          <Check className="h-3 w-3" />
                          {editing ? 'Sending…' : 'Save & Send'}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <SmartDataCard
                    role={m.role as any}
                    content={m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || (m as any).content || ''}
                    timestamp={formatMessageTime((m as any).createdAt)}
                    senderName={isAssistant ? (characterName ?? 'SYSTEM_RESPONSE') : 'Sensei'}
                    isStreaming={showStreamingCursor}
                    onEdit={!isAssistant && !showStreamingCursor && onEditMessage ? () => startEdit(m) : undefined}
                  />
                )}

                {/* Source preview cards — rendered under assistant messages.
                    Derived from tool-call logic entries in the turn's time
                    window. Shows RAG / Web / SQL / other tool outputs as
                    compact cards with worker icon + title + detail excerpt. */}
                {isAssistant && !showStreamingCursor && editingMessageId !== m.id && (
                  <SourcePreviewRow
                    message={m}
                    nextMessage={messages[idx + 1] ?? null}
                    logicEntries={logicEntries}
                  />
                )}

                {/* Branch selector + action buttons */}
                {messageTree && messageTree.length > 0 && editingMessageId !== m.id && (
                  <MessageActions
                    message={m}
                    messageTree={messageTree}
                    isAssistant={isAssistant}
                    isStreaming={showStreamingCursor}
                    onRegenerate={onRegenerate}
                    regenerating={regenerating}
                    onStartEdit={onEditMessage ? () => startEdit(m) : undefined}
                    pulseCarousel={pulseCarouselForId === m.id}
                    selectBranch={selectBranch}
                    nextBranch={nextBranch}
                    prevBranch={prevBranch}
                  />
                )}
            </div>
          </div>
        )
      })}

      {/* SQL Approval Card — shown when an interrupt is pending */}
      <SQLApprovalCardWrapper />

      {/* Note Confirmation Card — shown when a note delete/rewrite needs approval */}
      <NoteConfirmationCardWrapper />

      {/* Typing indicator — shown when waiting for first token (submitted state) */}
      {status === 'submitted' && <TypingIndicator />}

      {/* Fallback loading skeleton for history loading (no status available) */}
      {isLoading && status !== 'submitted' && status !== 'streaming' && (
          <div className="mx-auto flex max-w-5xl items-start gap-4">
               <div className="h-14 w-14 rounded-2xl bg-muted/60 animate-pulse flex-shrink-0" />
               <div className="flex-1 space-y-3 pt-1">
                 <div className="h-4 w-28 rounded-lg bg-muted/60 animate-pulse" />
                 <div className="rounded-2xl border border-border/50 p-5 space-y-2.5">
                   <div className="h-3.5 w-full rounded bg-muted/50 animate-pulse" />
                   <div className="h-3.5 w-[85%] rounded bg-muted/50 animate-pulse delay-75" />
                   <div className="h-3.5 w-[60%] rounded bg-muted/50 animate-pulse delay-150" />
                 </div>
               </div>
          </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} className="h-4" />
    </section>
  )
}

/** Renders the SQLApprovalCard only when there is a pending approval. */
function SQLApprovalCardWrapper() {
  const pending = useSQLApprovalStore((s) => s.pending)
  if (!pending) return null
  return (
    <div className="py-3">
      <SQLApprovalCard />
    </div>
  )
}

/** Renders the NoteConfirmationCard only when there is a pending confirmation. */
function NoteConfirmationCardWrapper() {
  const pending = useNoteConfirmationStore((s) => s.pending)
  if (!pending) return null
  return (
    <div className="py-3">
      <NoteConfirmationCard />
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * MessageActions — Branch selector + regenerate/edit buttons
 * ═══════════════════════════════════════════════════════════════════ */

interface MessageActionsProps {
  message: UIMessage
  messageTree: MessageNode[]
  isAssistant: boolean
  isStreaming: boolean
  onRegenerate?: (userMessageId: string) => void
  regenerating?: boolean
  /** Enter edit mode for a given user message id. */
  onStartEdit?: (userMessageId: string) => void
  /** Pulse the `< N/M >` carousel for ~1.5s to draw post-edit attention. */
  pulseCarousel?: boolean
  selectBranch: (parentId: string, childId: string) => void
  nextBranch: (parentId: string, siblings: MessageNode[]) => void
  prevBranch: (parentId: string, siblings: MessageNode[]) => void
}

/** Format ms-diff as a compact query-time badge, e.g. "1.4s" / "23s" / "2m 05s". */
function formatQueryTime(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return ''
  if (ms < 1000) return `${ms}ms`
  if (ms < 10_000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  const totalSec = Math.round(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}m ${s.toString().padStart(2, '0')}s`
}

function MessageActions({
  message,
  messageTree,
  isAssistant,
  isStreaming,
  onRegenerate,
  regenerating,
  onStartEdit,
  pulseCarousel,
  selectBranch,
  nextBranch,
  prevBranch,
}: MessageActionsProps) {
  const node = findNode(messageTree, message.id)
  if (!node) return null

  const siblings = node.parentId ? getSiblings(messageTree, message.id) : null
  const hasBranches = siblings && siblings.length > 1

  // Find the user message that this assistant message responds to (its parent)
  const userMessageId = isAssistant ? node.parentId : message.id

  return (
    <div className={cn(
      "flex items-center gap-2 mt-1.5 min-h-[24px]",
      isAssistant ? "justify-start" : "justify-end",
    )}>
      {/* Branch selector: < 1/3 >  — pulses briefly after an edit creates a new sibling */}
      {hasBranches && (
        <div className={cn(
          "flex items-center gap-0.5 select-none rounded-md transition-all",
          pulseCarousel && "animate-pulse ring-2 ring-rose-500/70 bg-rose-500/10 px-1",
        )}>
          <button
            onClick={(e) => { e.stopPropagation(); prevBranch(node.parentId!, siblings!) }}
            disabled={node.siblingIndex === 0}
            className="p-0.5 rounded transition-colors text-slate-500 hover:text-slate-300 disabled:opacity-20 disabled:cursor-default"
            aria-label="Previous branch"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className={cn(
            "text-[10px] font-bold tabular-nums min-w-[28px] text-center",
            pulseCarousel ? "text-rose-300" : "text-slate-500",
          )}>
            {node.siblingIndex + 1}/{node.siblingCount}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); nextBranch(node.parentId!, siblings!) }}
            disabled={node.siblingIndex === node.siblingCount - 1}
            className="p-0.5 rounded transition-colors text-slate-500 hover:text-slate-300 disabled:opacity-20 disabled:cursor-default"
            aria-label="Next branch"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Query-time badge (on assistant messages) — how long the response took,
          computed as createdAt(assistant) − createdAt(parent user message). */}
      {isAssistant && !isStreaming && (() => {
        const assistantAt = ((message as any).createdAt as Date | undefined)?.getTime()
        const parent = node.parentId ? findNode(messageTree, node.parentId) : null
        const userAt = parent?.message ? ((parent.message as any).createdAt as Date | undefined)?.getTime() : undefined
        if (!assistantAt || !userAt || assistantAt <= userAt) return null
        const label = formatQueryTime(assistantAt - userAt)
        if (!label) return null
        return (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[9px] font-mono text-slate-500 border border-slate-700/50 bg-slate-800/30"
            title="Time to process this query"
            aria-label={`Query processed in ${label}`}
          >
            <Clock className="h-2.5 w-2.5" />
            {label}
          </span>
        )
      })()}

      {/* Regenerate button (on assistant messages, when not streaming) */}
      {isAssistant && !isStreaming && onRegenerate && userMessageId && (
        <button
          onClick={() => onRegenerate(userMessageId)}
          disabled={regenerating}
          className={cn(
            "p-1 rounded-lg transition-all text-slate-500 hover:text-slate-300 hover:bg-white/5",
            "opacity-0 group-hover:opacity-100",
            regenerating && "animate-spin opacity-100 text-rose-400",
          )}
          title="Regenerate response"
          aria-label="Regenerate response"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      )}

    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * SourcePreviewRow — rich cards for RAG / Web / tool outputs
 *
 * Renders the tool-call logic entries that happened DURING the
 * assistant's turn (time window between the parent user message and
 * the next message). Each card shows:
 *   - Worker-appropriate icon (Database for rag/knowledge,
 *     Globe for web/search, Code2 for sql, Wrench for generic tools).
 *   - Worker name as the card title (e.g. "RAG", "WEB").
 *   - Detail excerpt (content_preview from the SSE event, truncated).
 *   - Linkified URLs inside the detail — first URL becomes the card's
 *     primary action (ExternalLink icon + open-in-new-tab).
 *
 * NOTE: This uses existing logic_entries data so no backend schema
 * change is required. True OG unfurling (favicon, og:image) still
 * needs backend work and is queued for a future round.
 * ═══════════════════════════════════════════════════════════════════ */

const WORKER_META: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; tone: string }> = {
  rag:       { icon: Database, label: 'RAG',       tone: 'cyan' },
  knowledge: { icon: Database, label: 'KB',        tone: 'cyan' },
  kb:        { icon: Database, label: 'KB',        tone: 'cyan' },
  retrieval: { icon: Database, label: 'DOC',       tone: 'cyan' },
  web:       { icon: Globe,    label: 'WEB',       tone: 'sky' },
  search:    { icon: Globe,    label: 'SEARCH',    tone: 'sky' },
  sql:       { icon: Code2,    label: 'SQL',       tone: 'emerald' },
}
function toneClasses(tone: string): { icon: string; border: string; bg: string; label: string } {
  switch (tone) {
    case 'cyan':    return { icon: 'text-cyan-300', border: 'border-cyan-500/30', bg: 'bg-cyan-500/5 hover:bg-cyan-500/10', label: 'text-cyan-300' }
    case 'sky':     return { icon: 'text-sky-300', border: 'border-sky-500/30', bg: 'bg-sky-500/5 hover:bg-sky-500/10', label: 'text-sky-300' }
    case 'emerald': return { icon: 'text-emerald-300', border: 'border-emerald-500/30', bg: 'bg-emerald-500/5 hover:bg-emerald-500/10', label: 'text-emerald-300' }
    default:        return { icon: 'text-violet-300', border: 'border-violet-500/30', bg: 'bg-violet-500/5 hover:bg-violet-500/10', label: 'text-violet-300' }
  }
}

function extractFirstUrl(s: string | null | undefined): string | null {
  if (!s) return null
  const match = s.match(/https?:\/\/[^\s)\]'"]+/)
  return match ? match[0] : null
}

function extractWorkerName(title: string): string {
  const m = title.match(/^([A-Za-z][\w-]*)/)
  return m ? m[1].toLowerCase() : 'tool'
}

interface SourcePreviewRowProps {
  message: UIMessage
  nextMessage: UIMessage | null
  logicEntries: LogicEntry[]
}

function SourcePreviewRow({ message, nextMessage, logicEntries }: SourcePreviewRowProps) {
  const msgAt = ((message as any).createdAt as Date | undefined)?.getTime() ?? 0
  const nextAt = nextMessage
    ? ((nextMessage as any).createdAt as Date | undefined)?.getTime() ?? Infinity
    : Infinity

  // Tool-call entries within the assistant's turn window.
  const tools = logicEntries.filter(
    (e) => e.kind === 'tool-call' && e.timestamp >= msgAt && e.timestamp < nextAt,
  )
  if (tools.length === 0) return null

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
        Sources · {tools.length}
      </p>
      <div className="flex flex-col gap-1.5">
        {tools.map((entry) => {
          const worker = extractWorkerName(entry.title)
          const meta = WORKER_META[worker] ?? { icon: Wrench, label: worker.toUpperCase().slice(0, 6), tone: 'violet' }
          const tones = toneClasses(meta.tone)
          const Icon = meta.icon
          const url = extractFirstUrl(entry.detail)
          const inner = (
            <div className={cn(
              "flex items-start gap-2 rounded-lg border px-2.5 py-1.5 transition-colors",
              tones.border, tones.bg,
            )}>
              <div className={cn("flex-shrink-0 mt-0.5", tones.icon)}>
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className={cn("text-[8px] font-black uppercase tracking-wider", tones.label)}>
                    {meta.label}
                  </span>
                  <span className="text-[10px] font-bold text-slate-200 truncate flex-1">
                    {entry.title}
                  </span>
                  {url && <ExternalLink className="h-2.5 w-2.5 text-slate-500 flex-shrink-0" />}
                </div>
                {entry.detail && (
                  <p className="text-[10px] text-slate-400 mt-0.5 line-clamp-2 break-words">
                    {entry.detail}
                  </p>
                )}
              </div>
            </div>
          )
          return url ? (
            <a
              key={entry.id}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
              title={url}
            >
              {inner}
            </a>
          ) : (
            <div key={entry.id}>{inner}</div>
          )
        })}
      </div>
    </div>
  )
}
