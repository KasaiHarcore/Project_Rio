"use client"

import React, { useState } from 'react'
import { cn } from '@/shared/lib/utils'
import { useNoteStore } from '@/features/notes/store'
import { useRouter } from 'next/navigation'
import { X, ExternalLink, Edit3, Eye } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

export function NotePopup() {
    const popupNoteId = useNoteStore((s) => s.popupNoteId)
    const popupNote = useNoteStore((s) => s.notes.find((n) => n.id === s.popupNoteId))
    const setPopupNoteId = useNoteStore((s) => s.setPopupNoteId)
    const updateNote = useNoteStore((s) => s.updateNote)
    const router = useRouter()

    const [viewMode, setViewMode] = useState<'preview' | 'edit'>('preview')

    if (!popupNoteId || !popupNote) return null

    const handleOpenInNotes = () => {
        setPopupNoteId(null)
        router.push(`/notes/${popupNote.id}`)
    }

    const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        updateNote(popupNote.id, { content: e.target.value })
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={() => setPopupNoteId(null)}
            />

            {/* Modal */}
            <div
                className="relative z-10 w-full max-w-2xl h-[80vh] flex flex-col rounded-2xl border overflow-hidden animate-in fade-in zoom-in-95 duration-200"
                style={{
                    background: 'var(--note-popup-bg)',
                    borderColor: 'var(--note-popup-border)',
                    boxShadow: 'var(--note-popup-shadow)',
                }}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--note-toolbar-border)] bg-[var(--note-toolbar-bg)]">
                    <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-3">
                            <h3 className="text-lg font-bold text-[var(--note-heading)] truncate">
                                {popupNote.title || 'Untitled Note'}
                            </h3>
                            <span className={cn(
                                "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md shrink-0",
                                popupNote.author === 'agent'
                                    ? "bg-[var(--note-accent)]/15 text-[var(--note-accent)]"
                                    : "bg-sky-500/15 text-sky-400"
                            )}>
                                {popupNote.author === 'agent' ? 'Agent' : 'You'}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        {/* View Toggle */}
                        <div className="flex items-center bg-black/20 rounded-lg p-1 border border-white/5 mr-2">
                            <button
                                onClick={() => setViewMode('preview')}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all",
                                    viewMode === 'preview' ? "bg-slate-700 text-white shadow-md" : "text-slate-400 hover:text-white"
                                )}
                            >
                                <Eye size={12} /> View
                            </button>
                            <button
                                onClick={() => setViewMode('edit')}
                                className={cn(
                                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all",
                                    viewMode === 'edit' ? "bg-[var(--note-accent)] text-white shadow-md shadow-rose-500/20" : "text-slate-400 hover:text-white"
                                )}
                            >
                                <Edit3 size={12} /> Edit
                            </button>
                        </div>

                        <button
                            onClick={handleOpenInNotes}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider text-[var(--note-accent)] hover:bg-[var(--note-toolbar-btn-hover)] bg-[var(--note-accent)]/10 transition-colors border border-[var(--note-accent)]/20"
                        >
                            Open
                            <ExternalLink size={14} />
                        </button>
                        <button
                            onClick={() => setPopupNoteId(null)}
                            className="p-2 rounded-lg text-[var(--note-muted)] hover:text-white hover:bg-white/10 transition-colors ml-1"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    {viewMode === 'edit' ? (
                        <textarea
                            value={popupNote.content || ''}
                            onChange={handleContentChange}
                            placeholder="Write your note in Markdown... Use # for headings, ** for bold, $$ for math."
                            className="w-full h-full min-h-[400px] p-6 bg-transparent resize-none border-none outline-none text-sm leading-relaxed text-[var(--note-text)] placeholder:text-[var(--note-muted)]"
                            spellCheck={false}
                            autoFocus
                        />
                    ) : (
                        <div className="p-6">
                            <article className="prose prose-sm prose-invert prose-rose max-w-none prose-pre:bg-[#0d1117] prose-pre:border prose-pre:border-white/10 prose-img:rounded-xl prose-img:border prose-img:border-white/10">
                                {popupNote.content ? (
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm, remarkMath]}
                                        rehypePlugins={[rehypeKatex]}
                                    >
                                        {popupNote.content}
                                    </ReactMarkdown>
                                ) : (
                                    <p className="text-slate-500 italic">Empty note</p>
                                )}
                            </article>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
