"use client"

import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { useNoteStore, type Note } from '@/store/note-store'
import {
    Search, Plus, Pin, MoreHorizontal,
    Pencil, Trash2, FolderPlus, Star,
    StickyNote, LayoutGrid, List,
    Loader2,
} from 'lucide-react'

/* ═══════════════════════════════════════════════════════════════════ */

function relativeTime(iso: string): string {
    if (!iso) return ''
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return 'Just now'
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    const diffDay = Math.floor(diffHr / 24)
    if (diffDay === 1) return 'Yesterday'
    if (diffDay < 7) return d.toLocaleDateString('en-US', { weekday: 'short' })
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/* ═══════════════════════════════════════════════════════════════════ */

interface NoteListProps {
    onNewNote: () => void
}

export function NoteList({ onNewNote }: NoteListProps) {
    const notes = useNoteStore((s) => s.getFilteredNotes())
    const collections = useNoteStore((s) => s.collections)
    const activeNoteId = useNoteStore((s) => s.activeNoteId)
    const searchQuery = useNoteStore((s) => s.searchQuery)
    const setSearchQuery = useNoteStore((s) => s.setSearchQuery)
    const setActiveNoteId = useNoteStore((s) => s.setActiveNoteId)
    const loading = useNoteStore((s) => s.loading)
    const viewMode = useNoteStore((s) => s.viewMode)
    const setViewMode = useNoteStore((s) => s.setViewMode)
    const activeCollectionId = useNoteStore((s) => s.activeCollectionId)
    const setActiveCollectionId = useNoteStore((s) => s.setActiveCollectionId)

    const [menuOpenId, setMenuOpenId] = useState<string | null>(null)

    const removeNote = useNoteStore((s) => s.removeNote)
    const updateNote = useNoteStore((s) => s.updateNote)

    const getCollectionName = (colId?: string) => {
        if (!colId) return null
        const col = collections.find((c) => c.id === colId)
        return col?.name ?? null
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-[var(--note-card-border)] flex flex-col gap-4">
                <div className="flex items-center justify-between">
                    <h1 className="text-xl font-black tracking-widest text-page-title">
                        {activeCollectionId
                            ? collections.find(c => c.id === activeCollectionId)?.name ?? 'COLLECTION'
                            : 'NOTES'
                        }
                    </h1>
                    <div className="flex items-center gap-2">
                        {/* View mode toggle */}
                        <button
                            onClick={() => setViewMode(viewMode === 'list' ? 'collections' : 'list')}
                            className="p-2 rounded-full transition-colors text-slate-400 hover:bg-[var(--note-toolbar-btn-hover)] hover:text-[var(--note-accent)]"
                            title={viewMode === 'list' ? 'View collections' : 'View all notes'}
                        >
                            {viewMode === 'list' ? <LayoutGrid size={18} /> : <List size={18} />}
                        </button>
                        {activeCollectionId && (
                            <button
                                onClick={() => setActiveCollectionId(null)}
                                className="px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider text-[var(--note-accent)] hover:bg-[var(--note-toolbar-btn-hover)] transition-colors"
                            >
                                All Notes
                            </button>
                        )}
                        <button
                            onClick={onNewNote}
                            className="p-2 rounded-full transition-colors bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-900/20"
                        >
                            <Plus size={20} />
                        </button>
                    </div>
                </div>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-2.5 text-slate-400 w-4 h-4" />
                    <input
                        placeholder="Search notes..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 rounded-xl border text-sm font-bold focus:outline-none focus:ring-2 transition-all bg-[var(--page-search-bg)] border-[var(--page-search-border)] text-[var(--page-search-text)] placeholder:text-[var(--page-search-placeholder)] focus:ring-[var(--page-search-focus-ring)]"
                    />
                </div>
            </div>

            {/* Note List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-rose-500" />
                    </div>
                ) : notes.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center px-4">
                        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4">
                            <StickyNote size={32} className="opacity-20 text-slate-400" />
                        </div>
                        <p className="text-sm font-bold text-page-muted mb-1">No notes yet</p>
                        <p className="text-xs text-[var(--note-muted)]">
                            Create your first note or start a chat session
                        </p>
                    </div>
                ) : (
                    /* Table-style list (Genio Home layout) */
                    <div className="divide-y divide-[var(--note-divider)]">
                        {/* Column headers */}
                        <div className="grid grid-cols-[1fr_140px_130px_32px] px-4 py-2.5 text-[9px] font-black uppercase tracking-[0.2em] text-[var(--note-muted)]">
                            <span>Note</span>
                            <span>Collection</span>
                            <span>Modified</span>
                            <span />
                        </div>

                        {notes.map((note) => {
                            const colName = getCollectionName(note.collectionId)
                            return (
                                <div
                                    key={note.id}
                                    onClick={() => setActiveNoteId(note.id)}
                                    className={cn(
                                        "group grid grid-cols-[1fr_140px_130px_32px] px-4 py-3 cursor-pointer transition-all items-center",
                                        activeNoteId === note.id
                                            ? "bg-rose-900/10"
                                            : "hover:bg-[var(--note-card-hover-bg)]",
                                    )}
                                >
                                    {/* Title */}
                                    <div className="flex items-center gap-2 min-w-0">
                                        {note.isPinned && <Pin size={12} className="shrink-0 text-[var(--note-accent)]" />}
                                        {note.isImportant && <Star size={12} className="shrink-0 text-amber-400 fill-amber-400" />}
                                        <span className={cn(
                                            "text-sm font-semibold truncate",
                                            activeNoteId === note.id ? "text-[var(--note-accent)]" : "text-[var(--note-heading)]"
                                        )}>
                                            {note.title || 'Untitled Note'}
                                        </span>
                                        {note.threadId && (
                                            <span className="shrink-0 text-[7px] font-bold uppercase px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400">
                                                Chat
                                            </span>
                                        )}
                                    </div>

                                    {/* Collection badge */}
                                    <div>
                                        {colName ? (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    if (note.collectionId) setActiveCollectionId(note.collectionId)
                                                }}
                                                className="text-xs font-semibold text-[var(--note-accent)] hover:underline truncate"
                                            >
                                                {colName}
                                            </button>
                                        ) : (
                                            <button
                                                onClick={(e) => { e.stopPropagation() }}
                                                className="text-[10px] font-medium text-[var(--note-muted)] hover:text-[var(--note-accent)] transition-colors opacity-0 group-hover:opacity-100"
                                            >
                                                Add to Collection
                                            </button>
                                        )}
                                    </div>

                                    {/* Date */}
                                    <span className="text-[11px] font-medium text-[var(--note-muted)]">
                                        {relativeTime(note.updatedAt)}
                                    </span>

                                    {/* Menu */}
                                    <div className="relative" onClick={(e) => e.stopPropagation()}>
                                        <button
                                            onClick={() => setMenuOpenId(menuOpenId === note.id ? null : note.id)}
                                            className={cn(
                                                "p-1 rounded-lg transition-all",
                                                menuOpenId === note.id
                                                    ? "bg-rose-900/20 text-rose-400"
                                                    : "opacity-0 group-hover:opacity-100 text-slate-400 hover:text-[var(--note-accent)]"
                                            )}
                                        >
                                            <MoreHorizontal size={14} />
                                        </button>

                                        {menuOpenId === note.id && (
                                            <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border shadow-xl py-1 backdrop-blur-xl animate-in fade-in slide-in-from-top-1 duration-150 bg-[#161b22] border-rose-900/30 shadow-black/40">
                                                <NoteMenuBtn
                                                    icon={<Pencil size={13} />}
                                                    label="Rename"
                                                    onClick={() => { setMenuOpenId(null) }}
                                                />
                                                <NoteMenuBtn
                                                    icon={<Pin size={13} className={note.isPinned ? "text-rose-400" : ""} />}
                                                    label={note.isPinned ? "Unpin" : "Pin"}
                                                    onClick={() => {
                                                        updateNote(note.id, { isPinned: !note.isPinned })
                                                        setMenuOpenId(null)
                                                    }}
                                                />
                                                <NoteMenuBtn
                                                    icon={<FolderPlus size={13} />}
                                                    label="Move to Collection"
                                                    onClick={() => { setMenuOpenId(null) }}
                                                />
                                                <div className="my-1 h-px bg-rose-900/20" />
                                                <NoteMenuBtn
                                                    icon={<Trash2 size={13} />}
                                                    label="Delete"
                                                    danger
                                                    onClick={() => {
                                                        removeNote(note.id)
                                                        setMenuOpenId(null)
                                                    }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t flex justify-between items-center text-[10px] font-bold uppercase tracking-wider bg-[#010409] border-[var(--note-card-border)] text-slate-600">
                <span>{notes.length} Notes</span>
                <span>{collections.length} Collections</span>
            </div>
        </div>
    )
}

/* ── Menu button ── */
function NoteMenuBtn({ icon, label, danger, onClick }: {
    icon: React.ReactNode; label: string; danger?: boolean; onClick: () => void
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold transition-colors text-left",
                danger
                    ? "text-red-400 hover:bg-red-500/10"
                    : "text-slate-300 hover:bg-rose-900/15 hover:text-slate-100"
            )}
        >
            {icon}
            {label}
        </button>
    )
}
