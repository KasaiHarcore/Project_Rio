"use client"

import React, { useEffect, useCallback, Suspense } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { cn } from '@/lib/utils'
import { useNoteStore, noteUid, blockUid } from '@/store/note-store'
import { apiListNotes, apiCreateNote, apiDeleteNote } from '@/lib/api'
import { useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { NoteList } from '@/components/features/notes/NoteList'
import { NoteEditor } from '@/components/features/notes/NoteEditor'
import { NoteCollections } from '@/components/features/notes/NoteCollections'
import { NoteSidePanel } from '@/components/features/notes/NoteSidePanel'

/* ═══════════════════════════════════════════════════════════════════ */

function NotesPageContent() {
    const viewMode = useNoteStore((s) => s.viewMode)
    const activeNoteId = useNoteStore((s) => s.activeNoteId)
    const setActiveNoteId = useNoteStore((s) => s.setActiveNoteId)
    const addNote = useNoteStore((s) => s.addNote)
    const setNotes = useNoteStore((s) => s.setNotes)
    const setLoading = useNoteStore((s) => s.setLoading)
    const loading = useNoteStore((s) => s.loading)

    const searchParams = useSearchParams()

    // Fetch notes on mount
    useEffect(() => {
        let cancelled = false
        async function load() {
            setLoading(true)
            try {
                const records = await apiListNotes()
                if (!cancelled) {
                    const notes = records.map((r) => ({
                        id: r.id,
                        title: r.title,
                        content: r.content,
                        blocks: [],
                        collectionId: r.collection_id,
                        threadId: r.thread_id,
                        isPinned: r.is_pinned,
                        isImportant: r.is_important,
                        author: r.author,
                        createdAt: r.created_at,
                        updatedAt: r.updated_at,
                        todos: r.todos ?? [],
                    }))
                    setNotes(notes)
                }
            } catch {
                // Backend unavailable — keep empty state
            } finally {
                if (!cancelled) setLoading(false)
            }
        }
        load()
        return () => { cancelled = true }
    }, [setNotes, setLoading])

    // Deep-link: ?note=<id>
    useEffect(() => {
        const noteParam = searchParams.get('note')
        if (noteParam) {
            setActiveNoteId(noteParam)
        }
    }, [searchParams, setActiveNoteId])

    // Create a new note
    const handleNewNote = useCallback(() => {
        const now = new Date().toISOString()
        const newNote = {
            id: noteUid(),
            title: '',
            content: '',
            blocks: [
                { id: blockUid(), type: 'heading' as const, content: '' },
            ],
            isPinned: false,
            isImportant: false,
            author: 'user' as const,
            createdAt: now,
            updatedAt: now,
            todos: [],
        }
        addNote(newNote)
        setActiveNoteId(newNote.id)

        // Try persisting to backend (fire & forget)
        apiCreateNote({
            title: newNote.title,
            content: '',
            author: 'user',
        }).catch(() => { })
    }, [addNote, setActiveNoteId])

    return (
        <DashboardLayout>
            <PageTransition className="flex h-full w-full overflow-hidden">
                {/* Left Panel */}
                <aside className={cn(
                    "w-full md:w-[340px] lg:w-[400px] flex flex-col border-r backdrop-blur-xl z-20 transition-all absolute md:relative h-full",
                    activeNoteId ? "hidden md:flex" : "flex",
                    "border-[var(--note-card-border)] bg-[var(--note-page-bg)]"
                )}>
                    {viewMode === 'list' ? (
                        <NoteList onNewNote={handleNewNote} />
                    ) : (
                        <NoteCollections />
                    )}
                </aside>

                {/* Center Panel — Editor */}
                <main className={cn(
                    "flex-1 relative flex flex-col transition-colors",
                    !activeNoteId ? "hidden md:flex" : "flex",
                    "bg-[var(--note-editor-bg)]"
                )}>
                    {loading ? (
                        <div className="flex-1 flex items-center justify-center">
                            <Loader2 className="h-6 w-6 animate-spin text-rose-500" />
                        </div>
                    ) : (
                        <NoteEditor />
                    )}
                </main>

                {/* Right Panel — Side Panel (Audio/Transcript/Outline) */}
                {activeNoteId && (
                    <div className="hidden 2xl:flex">
                        <NoteSidePanel />
                    </div>
                )}
            </PageTransition>
        </DashboardLayout>
    )
}

export default function NotesPage() {
    return (
        <Suspense fallback={
            <DashboardLayout>
                <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-rose-500" />
                </div>
            </DashboardLayout>
        }>
            <NotesPageContent />
        </Suspense>
    )
}
