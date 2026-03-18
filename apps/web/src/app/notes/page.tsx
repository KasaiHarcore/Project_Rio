"use client"

import React, { useEffect, useCallback, Suspense } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { cn } from '@/shared/lib/utils'
import { useNoteStore, noteUid, blockUid } from '@/features/notes/store'
import { apiListNotes, apiCreateNote, apiDeleteNote, apiListCollections } from '@/features/notes/api'
import { useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { NoteList } from '@/features/notes/components/NoteList'
import { NoteEditor } from '@/features/notes/components/NoteEditor'
import { NoteCollections } from '@/features/notes/components/NoteCollections'
import { NoteSidePanel } from '@/features/notes/components/NoteSidePanel'

/* ═══════════════════════════════════════════════════════════════════ */

function NotesPageContent() {
    const viewMode = useNoteStore((s) => s.viewMode)
    const activeNoteId = useNoteStore((s) => s.activeNoteId)
    const setActiveNoteId = useNoteStore((s) => s.setActiveNoteId)
    const addNote = useNoteStore((s) => s.addNote)
    const setNotes = useNoteStore((s) => s.setNotes)
    const setCollections = useNoteStore((s) => s.setCollections)
    const setLoading = useNoteStore((s) => s.setLoading)
    const loading = useNoteStore((s) => s.loading)

    const searchParams = useSearchParams()

    useEffect(() => {
        let cancelled = false
        async function load() {
            setLoading(true)
            try {
                const [noteRecords, colRecords] = await Promise.all([
                    apiListNotes(),
                    apiListCollections(),
                ])
                if (!cancelled) {
                    const notes = noteRecords.map((r) => ({
                        id: r.id,
                        title: r.title,
                        content: r.content,
                        blocks: [],
                        collectionIds: r.collection_ids ?? [],
                        threadId: r.thread_id,
                        isPinned: r.pinned,
                        isImportant: r.is_important,
                        author: (r.source === 'agent' ? 'agent' : 'user') as 'agent' | 'user',
                        createdAt: r.created_at,
                        updatedAt: r.updated_at,
                        todos: r.todos ?? [],
                    }))
                    setNotes(notes)

                    const collections = colRecords.map((c) => ({
                        id: c.id,
                        name: c.name,
                        noteCount: c.note_count,
                        createdAt: c.created_at,
                    }))
                    setCollections(collections)
                }
            } catch {
                // Backend unavailable — keep empty state
            } finally {
                if (!cancelled) setLoading(false)
            }
        }
        load()
        return () => { cancelled = true }
    }, [setNotes, setCollections, setLoading])

    // Deep-link: ?note=<id>
    useEffect(() => {
        const noteParam = searchParams.get('note')
        if (noteParam) {
            setActiveNoteId(noteParam)
        }
    }, [searchParams, setActiveNoteId])

    const updateNote = useNoteStore((s) => s.updateNote)

    const handleNewNote = useCallback(() => {
        const now = new Date().toISOString()
        const tempId = noteUid()
        const newNote = {
            id: tempId,
            title: '',
            content: '',
            blocks: [
                { id: blockUid(), type: 'heading' as const, content: '' },
            ],
            collectionIds: [],
            isPinned: false,
            isImportant: false,
            author: 'user' as const,
            createdAt: now,
            updatedAt: now,
            todos: [],
        }
        addNote(newNote)
        setActiveNoteId(tempId)

        // Persist to backend and replace temp ID with the real one
        apiCreateNote({
            title: newNote.title,
            content: '',
            source: 'user',
        }).then((saved) => {
            // Swap the temp ID with the backend ID in local state
            const store = useNoteStore.getState()
            const updated = store.notes.map((n) =>
                n.id === tempId ? { ...n, id: saved.id } : n,
            )
            useNoteStore.setState({
                notes: updated,
                activeNoteId: store.activeNoteId === tempId ? saved.id : store.activeNoteId,
            })
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
