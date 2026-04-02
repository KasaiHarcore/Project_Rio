"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { cn } from '@/shared/lib/utils'
import { useSidebarStore, SIDEBAR_LIMITS, type MemoryEntry } from '@/features/chat/store'
import {
  BrainCircuit, X, Trash2, Plus, Tag,
  User, Bot, AlertCircle, Loader2,
} from 'lucide-react'

/* ─── Constants ──────────────────────────────────────────────────── */

const TAG_COLORS: Record<string, string> = {
  preference: 'bg-violet-500/20 text-violet-400',
  context:    'bg-sky-500/20 text-sky-400',
  rule:       'bg-amber-500/20 text-amber-400',
  fact:       'bg-emerald-500/20 text-emerald-400',
  note:       'bg-slate-500/20 text-slate-400',
  semantic:   'bg-violet-500/20 text-violet-400',
  episodic:   'bg-sky-500/20 text-sky-400',
  procedural: 'bg-amber-500/20 text-amber-400',
}

const SUGGESTED_TAGS = ['preference', 'context', 'rule', 'fact', 'note'] as const

/* ─── Props ──────────────────────────────────────────────────────── */

interface MemoryTabProps {
  threadId: string | null
}

/* ═══════════════════════════════════════════════════════════════════ */

export function MemoryTab({ threadId }: MemoryTabProps) {
  const memoryEntries = useSidebarStore((s) => s.memoryEntries)
  const persistedMemories = useSidebarStore((s) => s.persistedMemories)
  const memoriesLoading = useSidebarStore((s) => s.memoriesLoading)
  const addMemoryEntry = useSidebarStore((s) => s.addMemoryEntry)
  const removeMemoryEntry = useSidebarStore((s) => s.removeMemoryEntry)
  const clearMemoryEntries = useSidebarStore((s) => s.clearMemoryEntries)
  const fetchThreadMemories = useSidebarStore((s) => s.fetchThreadMemories)

  const [addOpen, setAddOpen] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [newTag, setNewTag] = useState<string>('note')

  useEffect(() => {
    if (threadId) {
      fetchThreadMemories(threadId)
    }
  }, [threadId, fetchThreadMemories])

  function handleAdd() {
    if (!newContent.trim()) return
    addMemoryEntry({
      content: newContent.trim(),
      author: 'user',
      tag: newTag,
    })
    setNewContent('')
    setAddOpen(false)
  }

  const allEntries = useMemo(() => {
    const seenContent = new Set<string>()
    const merged: MemoryEntry[] = []

    for (const entry of persistedMemories) {
      if (!seenContent.has(entry.content)) {
        seenContent.add(entry.content)
        merged.push(entry)
      }
    }
    for (const entry of memoryEntries) {
      if (!seenContent.has(entry.content)) {
        seenContent.add(entry.content)
        merged.push(entry)
      }
    }
    return merged
  }, [persistedMemories, memoryEntries])

  const hasPersisted = persistedMemories.length > 0
  const headerLabel = hasPersisted ? 'Thread Memory' : 'Session Memory'

  return (
    <div className="space-y-0">
      {/* ───── Header bar ───── */}
      <div className="flex items-center justify-between p-4 pb-3 border-b border-[var(--chat-sidebar-section-border)]">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-3.5 w-3.5 text-[var(--chat-sidebar-stat-text)]" />
          <h3 className="text-[10px] font-black tracking-[0.25em] uppercase text-[var(--chat-sidebar-heading)]">
            {headerLabel}
          </h3>
          {memoriesLoading && (
            <Loader2 className="h-3 w-3 animate-spin text-[var(--chat-sidebar-stat-label)]" />
          )}
        </div>
        <div className="flex items-center gap-1">
          {memoryEntries.length > 0 && (
            <button
              onClick={clearMemoryEntries}
              className="rounded-md p-1 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-colors"
              title="Clear session memory"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
          <button
            onClick={() => { if (allEntries.length < SIDEBAR_LIMITS.MEMORY_ENTRIES) setAddOpen(!addOpen) }}
            className={cn(
              "rounded-md p-1 transition-colors hover:bg-[var(--chat-sidebar-artifact-bg)]",
              allEntries.length >= SIDEBAR_LIMITS.MEMORY_ENTRIES
                ? "text-[var(--chat-sidebar-stat-label)]/30 cursor-not-allowed"
                : "text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)]"
            )}
            title={allEntries.length >= SIDEBAR_LIMITS.MEMORY_ENTRIES ? `Max ${SIDEBAR_LIMITS.MEMORY_ENTRIES} entries` : 'Add memory entry'}
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* ───── Hint banner ───── */}
        <div className="flex items-start gap-2 rounded-lg px-2.5 py-2 bg-[var(--chat-sidebar-artifact-bg)]/40 border border-[var(--chat-sidebar-artifact-border)]/50">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0 text-[var(--chat-sidebar-stat-label)]" />
          <p className="text-[8px] leading-snug text-[var(--chat-sidebar-stat-label)]">
            The agent writes important context here during the conversation. You control what stays — remove anything the agent doesn't need.
          </p>
        </div>

        {/* ───── Add memory form ───── */}
        {addOpen && (
          <div className="rounded-xl border p-2.5 space-y-2 bg-[var(--chat-sidebar-card-bg)] border-[var(--chat-sidebar-card-border)]">
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Add something for the agent to remember..."
              rows={2}
              maxLength={SIDEBAR_LIMITS.TEXT_MAX_LENGTH}
              className="w-full resize-none rounded-lg border-none bg-transparent text-[10px] text-[var(--chat-sidebar-value)] placeholder:text-[var(--chat-sidebar-stat-label)]/50 focus:outline-none"
            />
            {newContent.length > SIDEBAR_LIMITS.TEXT_MAX_LENGTH * 0.8 && (
              <p className="text-[7px] text-amber-400/70 text-right">
                {newContent.length}/{SIDEBAR_LIMITS.TEXT_MAX_LENGTH}
              </p>
            )}
            {/* Tag picker */}
            <div className="flex items-center gap-1 flex-wrap">
              <Tag className="h-2.5 w-2.5 text-[var(--chat-sidebar-stat-label)]" />
              {SUGGESTED_TAGS.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setNewTag(tag)}
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-[7px] font-bold uppercase tracking-wider transition-all",
                    newTag === tag
                      ? TAG_COLORS[tag]
                      : "bg-transparent text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-value)]"
                  )}
                >
                  {tag}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-end gap-1.5">
              <button
                onClick={() => { setAddOpen(false); setNewContent('') }}
                className="rounded-md px-2 py-1 text-[8px] font-bold uppercase text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-value)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={!newContent.trim()}
                className="rounded-md px-2.5 py-1 text-[8px] font-bold uppercase bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 disabled:opacity-30 transition-colors"
              >
                Remember
              </button>
            </div>
          </div>
        )}

        {/* ───── Entries ───── */}
        {allEntries.length === 0 && !addOpen && !memoriesLoading ? (
          <div className="rounded-xl border border-dashed p-6 text-center border-[var(--chat-sidebar-artifact-border)]">
            <BrainCircuit className="h-6 w-6 mx-auto mb-2 text-[var(--chat-sidebar-stat-label)]" />
            <p className="text-[10px] font-bold text-[var(--chat-sidebar-stat-label)]">
              Memory is empty
            </p>
            <p className="text-[8px] text-[var(--chat-sidebar-stat-label)]/70 mt-1">
              The agent will store important context here as the conversation progresses
            </p>
          </div>
        ) : (
          <div className="space-y-1.5 max-h-[50vh] overflow-y-auto custom-scrollbar">
            {allEntries.slice().reverse().map((entry) => {
              const tagColor = TAG_COLORS[entry.tag ?? 'note'] ?? TAG_COLORS.note
              const isPersisted = entry.id.startsWith('persisted_')
              return (
                <div
                  key={entry.id}
                  className="group relative rounded-xl border p-2.5 transition-all bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)] hover:border-[var(--chat-sidebar-artifact-hover-border)]"
                >
                  {/* Header: author + tag + remove */}
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      {entry.author === 'agent' ? (
                        <Bot className="h-2.5 w-2.5 text-[var(--chat-sidebar-stat-text)]" />
                      ) : (
                        <User className="h-2.5 w-2.5 text-sky-400" />
                      )}
                      <span className={cn(
                        "text-[7px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md",
                        entry.author === 'agent'
                          ? "bg-[var(--chat-sidebar-stat-text)]/15 text-[var(--chat-sidebar-stat-text)]"
                          : "bg-sky-500/15 text-sky-400"
                      )}>
                        {entry.author}
                      </span>
                      {entry.tag && (
                        <span className={cn("text-[7px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md", tagColor)}>
                          {entry.tag}
                        </span>
                      )}
                      {isPersisted && (
                        <span className="text-[7px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400">
                          saved
                        </span>
                      )}
                    </div>
                    {!isPersisted && (
                      <button
                        onClick={() => removeMemoryEntry(entry.id)}
                        className="rounded p-0.5 opacity-0 group-hover:opacity-100 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-all"
                        title="Remove from memory"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>

                  {/* Content */}
                  <p className="text-[10px] text-[var(--chat-sidebar-value)] leading-snug whitespace-pre-wrap line-clamp-3 break-words">
                    {entry.content}
                  </p>

                  {/* Timestamp */}
                  {entry.timestamp > 0 && (
                    <p className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/60 mt-1.5">
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
