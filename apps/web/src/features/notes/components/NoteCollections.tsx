"use client"

import React, { useState } from 'react'
import { cn } from '@/shared/lib/utils'
import { useNoteStore, noteUid, type Collection } from '@/features/notes/store'
import { Plus, FolderOpen, MoreHorizontal, Pencil, Trash2, X, Check, List } from 'lucide-react'

/* ═══════════════════════════════════════════════════════════════════ */

export function NoteCollections() {
    const collections = useNoteStore((s) => s.collections)
    const notes = useNoteStore((s) => s.notes)
    const addCollection = useNoteStore((s) => s.addCollection)
    const removeCollection = useNoteStore((s) => s.removeCollection)
    const updateCollection = useNoteStore((s) => s.updateCollection)
    const setActiveCollectionId = useNoteStore((s) => s.setActiveCollectionId)
    const setViewMode = useNoteStore((s) => s.setViewMode)

    const [creating, setCreating] = useState(false)
    const [newName, setNewName] = useState('')
    const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
    const [renamingId, setRenamingId] = useState<string | null>(null)
    const [renameValue, setRenameValue] = useState('')

    const handleCreate = () => {
        if (!newName.trim()) return
        addCollection({
            id: noteUid(),
            name: newName.trim(),
            noteCount: 0,
            createdAt: new Date().toISOString(),
        })
        setNewName('')
        setCreating(false)
    }

    const handleRename = (id: string) => {
        if (!renameValue.trim()) { setRenamingId(null); return }
        updateCollection(id, { name: renameValue.trim() })
        setRenamingId(null)
    }

    const handleSelectCollection = (colId: string) => {
        setActiveCollectionId(colId)
        setViewMode('list')
    }

    const getNotesForCollection = (colId: string) =>
        notes.filter((n) => (n.collectionIds ?? []).includes(colId)).length

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-[var(--note-card-border)] flex items-center justify-between">
                <h1 className="text-xl font-black tracking-widest text-page-title">COLLECTIONS</h1>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setViewMode('list')}
                        className="p-2 rounded-full transition-colors text-slate-400 hover:bg-[var(--note-toolbar-btn-hover)] hover:text-[var(--note-accent)]"
                        title="Back to notes"
                    >
                        <List size={18} />
                    </button>
                    <button
                        onClick={() => setCreating(true)}
                        className="p-2 rounded-full transition-colors bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-900/20"
                    >
                        <Plus size={20} />
                    </button>
                </div>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                {/* Create form */}
                {creating && (
                    <div className="mb-4 rounded-xl border p-4 bg-[var(--note-collection-bg)] border-[var(--note-collection-border)]">
                        <input
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false) }}
                            placeholder="Collection name..."
                            className="w-full bg-transparent text-sm font-semibold text-[var(--note-heading)] placeholder:text-[var(--note-muted)] focus:outline-none mb-3"
                            autoFocus
                        />
                        <div className="flex items-center justify-end gap-2">
                            <button
                                onClick={() => { setCreating(false); setNewName('') }}
                                className="px-3 py-1 text-[10px] font-bold uppercase text-[var(--note-muted)] hover:text-[var(--note-text)] transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={!newName.trim()}
                                className="px-3 py-1 text-[10px] font-bold uppercase bg-rose-600 hover:bg-rose-700 text-white rounded-lg disabled:opacity-30 transition-colors"
                            >
                                Create
                            </button>
                        </div>
                    </div>
                )}

                {collections.length === 0 && !creating ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4">
                            <FolderOpen size={32} className="opacity-20 text-slate-400" />
                        </div>
                        <p className="text-sm font-bold text-page-muted mb-1">No collections yet</p>
                        <p className="text-xs text-[var(--note-muted)]">
                            Organize your notes into collections
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {collections.map((col) => (
                            <div
                                key={col.id}
                                onClick={() => handleSelectCollection(col.id)}
                                className={cn(
                                    "group relative rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md",
                                    "bg-[var(--note-collection-bg)] border-[var(--note-collection-border)]",
                                    "hover:border-[var(--note-collection-hover-border)] hover:bg-[var(--note-card-hover-bg)]"
                                )}
                            >
                                <div className="flex items-start justify-between">
                                    {renamingId === col.id ? (
                                        <div className="flex items-center gap-1 flex-1 min-w-0" onClick={(e) => e.stopPropagation()}>
                                            <input
                                                value={renameValue}
                                                onChange={(e) => setRenameValue(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleRename(col.id)
                                                    if (e.key === 'Escape') setRenamingId(null)
                                                }}
                                                onBlur={() => handleRename(col.id)}
                                                className="flex-1 min-w-0 text-base font-bold bg-transparent border-none outline-none text-[var(--note-heading)]"
                                                autoFocus
                                            />
                                            <button onClick={() => handleRename(col.id)} className="p-0.5 rounded hover:bg-emerald-500/20 text-emerald-500">
                                                <Check size={14} />
                                            </button>
                                            <button onClick={() => setRenamingId(null)} className="p-0.5 rounded hover:bg-red-500/20 text-red-400">
                                                <X size={14} />
                                            </button>
                                        </div>
                                    ) : (
                                        <h3 className="text-base font-bold text-[var(--note-heading)] truncate">
                                            {col.name}
                                        </h3>
                                    )}

                                    {renamingId !== col.id && (
                                        <div className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
                                            <button
                                                onClick={() => setMenuOpenId(menuOpenId === col.id ? null : col.id)}
                                                className={cn(
                                                    "p-1 rounded-lg transition-all",
                                                    menuOpenId === col.id
                                                        ? "bg-rose-900/20 text-rose-400"
                                                        : "opacity-0 group-hover:opacity-100 text-slate-400 hover:text-[var(--note-accent)]"
                                                )}
                                            >
                                                <MoreHorizontal size={14} />
                                            </button>

                                            {menuOpenId === col.id && (
                                                <div className="absolute right-0 top-full mt-1 z-50 w-36 rounded-xl border shadow-xl py-1 backdrop-blur-xl bg-[#161b22] border-rose-900/30 shadow-black/40">
                                                    <button
                                                        onClick={() => {
                                                            setRenamingId(col.id)
                                                            setRenameValue(col.name)
                                                            setMenuOpenId(null)
                                                        }}
                                                        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-rose-900/15 hover:text-slate-100"
                                                    >
                                                        <Pencil size={13} />
                                                        Rename
                                                    </button>
                                                    <div className="my-1 h-px bg-rose-900/20" />
                                                    <button
                                                        onClick={() => { removeCollection(col.id); setMenuOpenId(null) }}
                                                        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/10"
                                                    >
                                                        <Trash2 size={13} />
                                                        Delete
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="mt-3 flex items-center justify-between">
                                    <span className="text-xs font-medium text-[var(--note-muted)]">
                                        {getNotesForCollection(col.id)} notes
                                    </span>
                                    <button
                                        onClick={(e) => { e.stopPropagation() }}
                                        className="w-7 h-7 rounded-full border border-[var(--note-collection-border)] flex items-center justify-center text-[var(--note-muted)] hover:text-[var(--note-accent)] hover:border-[var(--note-collection-hover-border)] transition-colors"
                                    >
                                        <Plus size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
