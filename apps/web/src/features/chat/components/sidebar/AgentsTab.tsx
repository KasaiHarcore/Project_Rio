"use client"

import React, { useState } from 'react'
import { cn } from '@/shared/lib/utils'
import { useSidebarStore } from '@/features/chat/store'
import { SIDEBAR_LIMITS } from '@/features/chat/store'
import {
  Brain, Lightbulb, Route, Wrench, Info,
  StickyNote, Pin, PinOff, X, Plus,
  CheckSquare, Square, ChevronDown, ChevronRight,
  ExternalLink,
} from 'lucide-react'
import { useNoteStore, noteUid, blockUid } from '@/features/notes/store'

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

/* ═══════════════════════════════════════════════════════════════════ */

export function AgentsTab() {
  const logicEntries = useSidebarStore((s) => s.logicEntries)
  const clearLogicEntries = useSidebarStore((s) => s.clearLogicEntries)
  const stickyNotes = useSidebarStore((s) => s.stickyNotes)
  const addStickyNote = useSidebarStore((s) => s.addStickyNote)
  const removeStickyNote = useSidebarStore((s) => s.removeStickyNote)
  const toggleStickyPin = useSidebarStore((s) => s.toggleStickyPin)
  const toggleStickyTodo = useSidebarStore((s) => s.toggleStickyTodo)

  /** Remove a note from the store and, if persisted, also from the backend. */
  function handleRemoveNote(note: { id: string; dbId?: string }) {
    removeStickyNote(note.id)
    if (note.dbId) {
      fetch(`/api/notes/${note.dbId}`, { method: 'DELETE' }).catch(() => { })
    }
  }

  const [logicExpanded, setLogicExpanded] = useState(true)
  const [notesExpanded, setNotesExpanded] = useState(true)
  const [newNoteOpen, setNewNoteOpen] = useState(false)
  const [newNoteText, setNewNoteText] = useState('')

  const pinnedNotes = stickyNotes.filter((n) => n.pinned)
  const unpinnedNotes = stickyNotes.filter((n) => !n.pinned)
  const sortedNotes = [...pinnedNotes, ...unpinnedNotes]

  /* ── Handle new user note ── */
  function handleAddNote() {
    if (!newNoteText.trim()) return
    // Parse TODO lines: lines starting with "- [ ]" or "- [x]"
    const lines = newNoteText.split('\n')
    const todoLines = lines.filter((l) => /^\s*-\s*\[[ x]\]/i.test(l))
    const todos = todoLines.length > 0
      ? todoLines.map((l) => ({
        text: l.replace(/^\s*-\s*\[[ x]\]\s*/i, ''),
        done: /\[x\]/i.test(l),
      }))
      : undefined

    addStickyNote({
      content: newNoteText,
      todos,
      author: 'user',
    })
    setNewNoteText('')
    setNewNoteOpen(false)
  }

  /* ── Open note in popup ── */
  const setPopupNoteId = useNoteStore((s) => s.setPopupNoteId)
  const addNoteToGlobal = useNoteStore((s) => s.addNote)

  function handleOpenNotePopup(note: { id: string; content: string; author: 'agent' | 'user'; timestamp: number; todos?: { text: string; done: boolean }[] }) {
    // Ensure note exists in global note store so popup can find it
    const existingNote = useNoteStore.getState().notes.find((n) => n.sidebarNoteId === note.id || n.id === note.id)
    if (existingNote) {
      setPopupNoteId(existingNote.id)
    } else {
      // Create a global note entry from the sidebar note
      const now = new Date().toISOString()
      const globalNote = {
        id: noteUid(),
        title: note.content.split('\n')[0].slice(0, 60) || 'Untitled Note',
        content: note.content,
        blocks: note.todos && note.todos.length > 0
          ? note.todos.map((t) => ({
            id: blockUid(),
            type: 'todo' as const,
            content: t.text,
            checked: t.done,
          }))
          : [{ id: blockUid(), type: 'text' as const, content: note.content }],
        sidebarNoteId: note.id,
        isPinned: false,
        isImportant: false,
        author: note.author,
        createdAt: new Date(note.timestamp).toISOString(),
        updatedAt: now,
        todos: note.todos ?? [],
      }
      addNoteToGlobal(globalNote)
      setPopupNoteId(globalNote.id)
    }
  }

  return (
    <div className="space-y-0">
      {/* ───── Logic Feed ───── */}
      <div className="border-b border-[var(--chat-sidebar-section-border)]">
        <div
          onClick={() => setLogicExpanded(!logicExpanded)}
          className="flex w-full items-center justify-between p-4 pb-2 text-left group cursor-pointer select-none"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setLogicExpanded(!logicExpanded) } }}
        >
          <div className="flex items-center gap-2">
            {logicExpanded ? <ChevronDown className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" /> : <ChevronRight className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" />}
            <h3 className="text-[10px] font-black tracking-[0.25em] uppercase text-[var(--chat-sidebar-heading)]">
              Logic
            </h3>
            {logicEntries.length > 0 && (
              <span className="ml-1 rounded-full px-1.5 py-0.5 text-[8px] font-bold bg-[var(--chat-sidebar-stat-text)]/20 text-[var(--chat-sidebar-stat-text)]">
                {logicEntries.length}
              </span>
            )}
          </div>
          {logicEntries.length > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); clearLogicEntries() }}
              className="text-[8px] font-bold uppercase tracking-wider text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)] transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {logicExpanded && (
          <div className="px-4 pb-4 space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
            {logicEntries.length === 0 ? (
              <div className="rounded-xl border border-dashed p-3 text-center border-[var(--chat-sidebar-artifact-border)]">
                <Lightbulb className="h-4 w-4 mx-auto mb-1 text-[var(--chat-sidebar-stat-label)]" />
                <p className="text-[9px] text-[var(--chat-sidebar-stat-label)]">
                  Agent thinking & decisions appear here
                </p>
              </div>
            ) : (
              logicEntries.slice().reverse().map((entry) => {
                const Icon = LOGIC_ICONS[entry.kind] ?? Info
                const color = LOGIC_COLORS[entry.kind] ?? 'text-slate-400'
                return (
                  <div
                    key={entry.id}
                    className="flex items-start gap-2 rounded-lg px-2.5 py-2 bg-[var(--chat-sidebar-artifact-bg)]/60 border border-[var(--chat-sidebar-artifact-border)]/50"
                  >
                    <Icon className={cn('h-3 w-3 mt-0.5 flex-shrink-0', color)} />
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-bold text-[var(--chat-sidebar-value)] leading-tight">{entry.title}</p>
                      {entry.detail && (
                        <p className="text-[8px] text-[var(--chat-sidebar-stat-label)] mt-0.5 leading-snug line-clamp-2">{entry.detail}</p>
                      )}
                      <p className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/60 mt-0.5">
                        {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </p>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* ───── Sticky Notes ───── */}
      <div className="border-[var(--chat-sidebar-section-border)]">
        <div
          onClick={() => setNotesExpanded(!notesExpanded)}
          className="flex w-full items-center justify-between p-4 pb-2 text-left cursor-pointer select-none"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setNotesExpanded(!notesExpanded) } }}
        >
          <div className="flex items-center gap-2">
            {notesExpanded ? <ChevronDown className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" /> : <ChevronRight className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" />}
            <h3 className="text-[10px] font-black tracking-[0.25em] uppercase text-[var(--chat-sidebar-heading)]">
              Notes
            </h3>
            {stickyNotes.length > 0 && (
              <span className="ml-1 rounded-full px-1.5 py-0.5 text-[8px] font-bold bg-amber-500/20 text-amber-400">
                {stickyNotes.length}
              </span>
            )}
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); if (stickyNotes.length < SIDEBAR_LIMITS.STICKY_NOTES) setNewNoteOpen(!newNoteOpen) }}
            className={cn(
              "rounded-md p-1 transition-colors hover:bg-[var(--chat-sidebar-artifact-bg)]",
              stickyNotes.length >= SIDEBAR_LIMITS.STICKY_NOTES
                ? "text-[var(--chat-sidebar-stat-label)]/30 cursor-not-allowed"
                : "text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)]"
            )}
            title={stickyNotes.length >= SIDEBAR_LIMITS.STICKY_NOTES ? `Max ${SIDEBAR_LIMITS.STICKY_NOTES} notes` : 'Add note'}
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {notesExpanded && (
          <div className="px-4 pb-4 space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
            {/* Quick add note form */}
            {newNoteOpen && (
              <div className="rounded-xl border p-2.5 space-y-2 bg-[var(--chat-sidebar-card-bg)] border-[var(--chat-sidebar-card-border)]">
                <textarea
                  value={newNoteText}
                  onChange={(e) => setNewNoteText(e.target.value)}
                  placeholder={"Write a note...\nUse - [ ] for TODO items"}
                  rows={3}
                  maxLength={SIDEBAR_LIMITS.TEXT_MAX_LENGTH}
                  className="w-full resize-none rounded-lg border-none bg-transparent text-[10px] text-[var(--chat-sidebar-value)] placeholder:text-[var(--chat-sidebar-stat-label)]/50 focus:outline-none"
                />
                {newNoteText.length > SIDEBAR_LIMITS.TEXT_MAX_LENGTH * 0.8 && (
                  <p className="text-[7px] text-amber-400/70 text-right">
                    {newNoteText.length}/{SIDEBAR_LIMITS.TEXT_MAX_LENGTH}
                  </p>
                )}
                <div className="flex items-center justify-end gap-1.5">
                  <button
                    onClick={() => { setNewNoteOpen(false); setNewNoteText('') }}
                    className="rounded-md px-2 py-1 text-[8px] font-bold uppercase text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-value)] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddNote}
                    disabled={!newNoteText.trim()}
                    className="rounded-md px-2.5 py-1 text-[8px] font-bold uppercase bg-[var(--chat-sidebar-stat-text)]/20 text-[var(--chat-sidebar-stat-text)] hover:bg-[var(--chat-sidebar-stat-text)]/30 disabled:opacity-30 transition-colors"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}

            {sortedNotes.length === 0 && !newNoteOpen ? (
              <div className="rounded-xl border border-dashed p-3 text-center border-[var(--chat-sidebar-artifact-border)]">
                <StickyNote className="h-4 w-4 mx-auto mb-1 text-[var(--chat-sidebar-stat-label)]" />
                <p className="text-[9px] text-[var(--chat-sidebar-stat-label)]">
                  Quick notes & TODOs appear here
                </p>
              </div>
            ) : (
              sortedNotes.map((note) => (
                <div
                  key={note.id}
                  onClick={() => handleOpenNotePopup(note)}
                  className={cn(
                    "group relative rounded-xl border p-2.5 transition-all cursor-pointer",
                    "bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)]",
                    "hover:border-[var(--chat-sidebar-artifact-hover-border)] hover:bg-[var(--chat-sidebar-artifact-hover-bg)]",
                    note.pinned && "border-amber-500/30 bg-amber-500/5"
                  )}
                >
                  {/* Note header */}
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "text-[7px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md",
                        note.author === 'agent'
                          ? "bg-[var(--chat-sidebar-stat-text)]/15 text-[var(--chat-sidebar-stat-text)]"
                          : "bg-sky-500/15 text-sky-400"
                      )}>
                        {note.author === 'agent' ? 'Agent' : 'You'}
                      </span>
                      {note.pinned && <Pin className="h-2.5 w-2.5 text-amber-400" />}
                    </div>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => toggleStickyPin(note.id)}
                        className="rounded p-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-amber-400 transition-colors"
                        title={note.pinned ? 'Unpin' : 'Pin'}
                      >
                        {note.pinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
                      </button>
                      <button
                        onClick={() => handleRemoveNote(note)}
                        className="rounded p-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-colors"
                        title="Remove"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* TODO items or plain text */}
                  {note.todos && note.todos.length > 0 ? (
                    <div className="space-y-1">
                      {note.todos.map((todo, i) => (
                        <button
                          key={i}
                          onClick={() => toggleStickyTodo(note.id, i)}
                          className="flex items-start gap-1.5 w-full text-left group/todo"
                        >
                          {todo.done
                            ? <CheckSquare className="h-3 w-3 mt-0.5 flex-shrink-0 text-emerald-400" />
                            : <Square className="h-3 w-3 mt-0.5 flex-shrink-0 text-[var(--chat-sidebar-stat-label)] group-hover/todo:text-[var(--chat-sidebar-stat-text)]" />
                          }
                          <span className={cn(
                            "text-[10px] leading-tight",
                            todo.done
                              ? "line-through text-[var(--chat-sidebar-stat-label)]"
                              : "text-[var(--chat-sidebar-value)]"
                          )}>
                            {todo.text}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-[var(--chat-sidebar-value)] leading-snug whitespace-pre-wrap line-clamp-4">
                      {note.content}
                    </p>
                  )}

                  <p className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/60 mt-1.5 flex items-center justify-between">
                    <span>{new Date(note.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleOpenNotePopup(note) }}
                      className="flex items-center gap-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-[var(--note-accent,#fb7185)] transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <span className="text-[7px] font-bold uppercase tracking-wider">Open</span>
                      <ExternalLink size={8} />
                    </button>
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
