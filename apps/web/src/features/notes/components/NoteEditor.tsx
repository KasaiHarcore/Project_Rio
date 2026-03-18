"use client"

import React, { useState, useRef, useCallback, useEffect } from 'react'
import { cn } from '@/shared/lib/utils'
import { useNoteStore, flushPendingSaves } from '@/features/notes/store'
import {
    Type, Edit3, Eye,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import Editor, { type OnMount } from '@monaco-editor/react'
import type * as Monaco from 'monaco-editor'

export function NoteEditor() {
    const activeNoteId = useNoteStore((s) => s.activeNoteId)
    const activeNote = useNoteStore((s) => s.notes.find((n) => n.id === s.activeNoteId))
    const updateNote = useNoteStore((s) => s.updateNote)

    const [editingTitle, setEditingTitle] = useState(false)
    const [titleValue, setTitleValue] = useState('')
    const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit')
    const titleRef = useRef<HTMLInputElement>(null)
    const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)
    const contentRef = useRef<string>('')

    // Sync title when note changes
    useEffect(() => {
        if (activeNote) setTitleValue(activeNote.title)
    }, [activeNote?.id]) // eslint-disable-line react-hooks/exhaustive-deps

    // Sync editor content when switching notes
    useEffect(() => {
        const newContent = activeNote?.content ?? ''
        contentRef.current = newContent
        if (editorRef.current) {
            const model = editorRef.current.getModel()
            if (model && model.getValue() !== newContent) {
                model.setValue(newContent)
            }
        }
    }, [activeNote?.id]) // eslint-disable-line react-hooks/exhaustive-deps

    // Flush pending saves on unmount / page leave
    useEffect(() => {
        const handleBeforeUnload = () => flushPendingSaves()
        window.addEventListener('beforeunload', handleBeforeUnload)
        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload)
            flushPendingSaves()
        }
    }, [])

    const handleTitleSubmit = useCallback(() => {
        if (activeNote && titleValue.trim()) {
            updateNote(activeNote.id, { title: titleValue.trim() })
        }
        setEditingTitle(false)
    }, [activeNote, titleValue, updateNote])

    const handleEditorMount: OnMount = useCallback((editor, monaco) => {
        editorRef.current = editor

        const model = editor.getModel()
        if (model && activeNote) {
            const currentVal = model.getValue()
            if (currentVal !== activeNote.content) {
                model.setValue(activeNote.content || '')
            }
        }

        // Listen for content changes
        editor.onDidChangeModelContent(() => {
            const value = editor.getValue()
            contentRef.current = value
            const noteId = useNoteStore.getState().activeNoteId
            if (noteId) {
                updateNote(noteId, { content: value })
            }
        })

        editor.getDomNode()?.addEventListener('paste', (e: ClipboardEvent) => {
            const items = e.clipboardData?.items
            if (!items) return

            for (let i = 0; i < items.length; i++) {
                const item = items[i]
                if (item.type.startsWith('image/')) {
                    e.preventDefault()
                    e.stopPropagation()

                    const file = item.getAsFile()
                    if (!file) return

                    const reader = new FileReader()
                    reader.onload = () => {
                        const base64 = reader.result as string
                        const ext = file.type.split('/')[1] || 'png'
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
                        const altText = `image-${timestamp}.${ext}`

                        const selection = editor.getSelection()
                        if (selection) {
                            const markdownImg = `![${altText}](${base64})\n`
                            editor.executeEdits('paste-image', [{
                                range: selection,
                                text: markdownImg,
                                forceMoveMarkers: true,
                            }])
                        }
                    }
                    reader.readAsDataURL(file)
                    return
                }
            }
        })

        // Focus editor
        editor.focus()
    }, [activeNote, updateNote]) // eslint-disable-line react-hooks/exhaustive-deps

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
            <div className="flex-1 overflow-hidden">
                {viewMode === 'edit' ? (
                    <Editor
                        key={activeNote.id}
                        defaultLanguage="markdown"
                        defaultValue={activeNote.content || ''}
                        theme="note-dark"
                        onMount={handleEditorMount}
                        beforeMount={(monaco) => {
                            monaco.editor.defineTheme('note-dark', {
                                base: 'vs-dark',
                                inherit: true,
                                rules: [
                                    { token: 'keyword', foreground: 'f87171' },
                                    { token: 'comment', foreground: '6b7280' },
                                    { token: 'string', foreground: 'fbbf24' },
                                    { token: 'emphasis', fontStyle: 'italic' },
                                    { token: 'strong', fontStyle: 'bold' },
                                ],
                                colors: {
                                    'editor.background': '#00000000',
                                    'editor.foreground': '#d1d5db',
                                    'editor.lineHighlightBackground': '#ffffff08',
                                    'editor.selectionBackground': '#f4364c30',
                                    'editor.inactiveSelectionBackground': '#f4364c15',
                                    'editorCursor.foreground': '#f43f5e',
                                    'editorLineNumber.foreground': '#374151',
                                    'editorLineNumber.activeForeground': '#6b7280',
                                    'editorIndentGuide.background': '#1f2937',
                                    'editorWidget.background': '#0d1117',
                                    'editorWidget.border': '#1f2937',
                                    'editorSuggestWidget.background': '#0d1117',
                                    'editorSuggestWidget.border': '#1f2937',
                                    'editorSuggestWidget.selectedBackground': '#f4364c20',
                                },
                            })
                        }}
                        options={{
                            fontSize: 14,
                            lineHeight: 24,
                            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
                            minimap: { enabled: false },
                            wordWrap: 'on',
                            lineNumbers: 'off',
                            glyphMargin: false,
                            folding: false,
                            lineDecorationsWidth: 0,
                            lineNumbersMinChars: 0,
                            renderLineHighlight: 'line',
                            scrollBeyondLastLine: false,
                            padding: { top: 24, bottom: 24 },
                            tabSize: 2,
                            insertSpaces: true,
                            autoIndent: 'full',
                            formatOnPaste: true,
                            quickSuggestions: false,
                            suggestOnTriggerCharacters: false,
                            parameterHints: { enabled: false },
                            overviewRulerBorder: false,
                            overviewRulerLanes: 0,
                            hideCursorInOverviewRuler: true,
                            scrollbar: {
                                vertical: 'auto',
                                horizontal: 'hidden',
                                verticalScrollbarSize: 6,
                            },
                            cursorBlinking: 'smooth',
                            cursorSmoothCaretAnimation: 'on',
                            smoothScrolling: true,
                            contextmenu: true,
                            multiCursorModifier: 'alt',
                            dragAndDrop: true,
                            links: true,
                            bracketPairColorization: { enabled: true },
                        }}
                    />
                ) : (
                    <div className="p-6 overflow-y-auto h-full custom-scrollbar">
                        <article className="prose prose-invert prose-rose max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-img:rounded-xl prose-img:border prose-img:border-white/10">
                            {activeNote.content ? (
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[rehypeKatex]}
                                    components={{
                                        img: ({ src, alt, ...props }) =>
                                            src ? <img src={src} alt={alt || ''} {...props} /> : null,
                                    }}
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
