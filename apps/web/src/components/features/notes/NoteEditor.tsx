"use client"

import React, { useState, useRef, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useNoteStore } from '@/store/note-store'
import {
    Type, Edit3, Eye,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

export function NoteEditor() {
    const activeNote = useNoteStore((s) => s.getActiveNote())
    const updateNote = useNoteStore((s) => s.updateNote)

    const [editingTitle, setEditingTitle] = useState(false)
    const [titleValue, setTitleValue] = useState('')
    const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit')
    const titleRef = useRef<HTMLInputElement>(null)

    // Sync title when note changes
    useEffect(() => {
        if (activeNote) setTitleValue(activeNote.title)
    }, [activeNote?.id]) // eslint-disable-line react-hooks/exhaustive-deps

    const handleTitleSubmit = useCallback(() => {
        if (activeNote && titleValue.trim()) {
            updateNote(activeNote.id, { title: titleValue.trim() })
        }
        setEditingTitle(false)
    }, [activeNote, titleValue, updateNote])

    const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (!activeNote) return
        updateNote(activeNote.id, { content: e.target.value })
    }, [activeNote, updateNote])

    if (!activeNote) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                <div className="w-24 h-24 rounded-full bg-white/5 flex items-center justify-center mb-4">
                    <Type size={36} className="opacity-20" />
                </div>
                <p className="font-bold tracking-widest text-sm text-page-muted">SELECT A NOTE</p>
                <p className="text-xs text-[var(--note-muted)] mt-1">Choose a note from the list to start editing</p>
            </div>
        )
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--note-editor-bg)]">
            {/* Title & Toolbar */}
            <div className="px-6 pt-6 pb-3 border-b border-[var(--note-editor-border)] bg-[var(--note-toolbar-bg)]">
                <div className="flex items-center justify-between mb-2">
                    {editingTitle ? (
                        <input
                            ref={titleRef}
                            value={titleValue}
                            onChange={(e) => setTitleValue(e.target.value)}
                            onBlur={handleTitleSubmit}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleTitleSubmit() }}
                            className="w-full text-2xl font-black tracking-wide bg-transparent border-none outline-none text-[var(--note-heading)] placeholder:text-[var(--note-muted)]"
                            placeholder="Note title..."
                            autoFocus
                        />
                    ) : (
                        <h2
                            onClick={() => { setEditingTitle(true); setTitleValue(activeNote.title) }}
                            className="text-2xl font-black tracking-wide text-[var(--note-heading)] cursor-text hover:opacity-80 transition-opacity flex-1 truncate mr-4"
                        >
                            {activeNote.title || 'Untitled Note'}
                        </h2>
                    )}

                    {/* View Toggle */}
                    <div className="flex items-center bg-black/20 rounded-lg p-1 border border-white/5 shrink-0">
                        <button
                            onClick={() => setViewMode('edit')}
                            className={cn(
                                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all",
                                viewMode === 'edit' ? "bg-[var(--note-accent)] text-white shadow-md shadow-rose-500/20" : "text-slate-400 hover:text-white"
                            )}
                        >
                            <Edit3 size={14} /> Edit
                        </button>
                        <button
                            onClick={() => setViewMode('preview')}
                            className={cn(
                                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all",
                                viewMode === 'preview' ? "bg-[var(--note-accent)] text-white shadow-md shadow-rose-500/20" : "text-slate-400 hover:text-white"
                            )}
                        >
                            <Eye size={14} /> Preview
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-3 text-[9px] font-bold uppercase tracking-wider text-[var(--note-muted)]">
                    <span>{activeNote.content?.length || 0} characters</span>
                    <span>·</span>
                    <span>{activeNote.author === 'agent' ? 'Agent' : 'You'}</span>
                    {activeNote.threadId && (
                        <>
                            <span>·</span>
                            <span className="text-[var(--note-accent)]">From chat</span>
                        </>
                    )}
                </div>
            </div>

            {/* Note content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {viewMode === 'edit' ? (
                    <textarea
                        value={activeNote.content || ''}
                        onChange={handleContentChange}
                        placeholder="Write your note in Markdown... Use # for headings, ** for bold, $$ for math."
                        className="w-full h-full min-h-[500px] p-6 bg-transparent resize-none border-none outline-none text-sm leading-relaxed text-[var(--note-text)] placeholder:text-[var(--note-muted)]"
                        spellCheck={false}
                    />
                ) : (
                    <div className="p-6">
                        <article className="prose prose-invert prose-rose max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-img:rounded-xl prose-img:border prose-img:border-white/10">
                            {activeNote.content ? (
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[rehypeKatex]}
                                >
                                    {activeNote.content}
                                </ReactMarkdown>
                            ) : (
                                <p className="text-slate-500 italic">Empty note</p>
                            )}
                        </article>
                    </div>
                )}
            </div>
        </div>
    )
}
