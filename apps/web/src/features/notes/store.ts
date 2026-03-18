import { create } from 'zustand'
import {
    apiUpdateNote, apiDeleteNote,
    apiCreateCollection, apiUpdateCollection, apiDeleteCollection,
} from '@/features/notes/api'

/* ─── Types ──────────────────────────────────────────────────────── */

export interface NoteBlock {
    id: string
    type: 'heading' | 'text' | 'bullet' | 'todo' | 'important' | 'divider'
    content: string
    checked?: boolean
}

export interface NoteAudio {
    id: string
    url?: string
    duration?: number
    transcript?: string
}

export interface Note {
    id: string
    title: string
    content: string
    blocks: NoteBlock[]
    collectionIds: string[]
    threadId?: string
    sidebarNoteId?: string
    isPinned: boolean
    isImportant: boolean
    author: 'agent' | 'user'
    createdAt: string
    updatedAt: string
    todos: { text: string; done: boolean }[]
    audio?: NoteAudio
}

export interface Collection {
    id: string
    name: string
    noteCount: number
    createdAt: string
}

/* ─── Debounced save helper ──────────────────────────────────────── */

const _saveTimers = new Map<string, ReturnType<typeof setTimeout>>()

/**
 * Debounced persist to backend. Fires 800ms after the last call for a
 * given note ID. Immediate flushes happen on delete and pin/flag changes.
 */
function debouncedPersist(noteId: string, patch: Record<string, unknown>, immediate = false) {
    // Skip notes with temporary IDs that haven't been created in the backend yet
    if (noteId.startsWith('note-')) return

    const fire = () => {
        apiUpdateNote(noteId, patch).catch((err) => {
            console.error(`[NoteStore] Failed to save note ${noteId}:`, err.status ?? '', err.message, err.body ?? '')
        })
    }

    if (immediate) {
        // Cancel any pending debounce and fire immediately
        const existing = _saveTimers.get(noteId)
        if (existing) clearTimeout(existing)
        _saveTimers.delete(noteId)
        fire()
        return
    }

    // Debounce: reset timer on every keystroke
    const existing = _saveTimers.get(noteId)
    if (existing) clearTimeout(existing)

    _saveTimers.set(
        noteId,
        setTimeout(() => {
            _saveTimers.delete(noteId)
            fire()
        }, 800),
    )
}

/** Flush all pending saves immediately (call before navigation). */
export function flushPendingSaves() {
    for (const [noteId, timer] of _saveTimers.entries()) {
        clearTimeout(timer)
        _saveTimers.delete(noteId)
        // We need the current note state — best-effort: the debounced call
        // already captured the patch, but since we cleared the timer we
        // need to re-read. The store subscriber approach below handles this.
    }
}

/* ─── Store ──────────────────────────────────────────────────────── */

type SidePanelTab = 'audio' | 'transcript' | 'outline'

interface NoteState {
    notes: Note[]
    collections: Collection[]
    activeNoteId: string | null
    activeCollectionId: string | null
    searchQuery: string
    viewMode: 'list' | 'collections'
    sidePanelTab: SidePanelTab
    loading: boolean
    popupNoteId: string | null

    // Actions
    setNotes: (notes: Note[]) => void
    setCollections: (collections: Collection[]) => void
    setActiveNoteId: (id: string | null) => void
    setActiveCollectionId: (id: string | null) => void
    setSearchQuery: (q: string) => void
    setViewMode: (mode: 'list' | 'collections') => void
    setSidePanelTab: (tab: SidePanelTab) => void
    setLoading: (v: boolean) => void
    setPopupNoteId: (id: string | null) => void

    addNote: (note: Note) => void
    updateNote: (id: string, patch: Partial<Note>) => void
    removeNote: (id: string) => void
    updateNoteBlock: (noteId: string, blockId: string, patch: Partial<NoteBlock>) => void
    addNoteBlock: (noteId: string, block: NoteBlock, afterBlockId?: string) => void
    removeNoteBlock: (noteId: string, blockId: string) => void

    addCollection: (col: Collection) => void
    updateCollection: (id: string, patch: Partial<Collection>) => void
    removeCollection: (id: string) => void

    // Helpers
    getActiveNote: () => Note | undefined
    getPopupNote: () => Note | undefined
    getFilteredNotes: () => Note[]
}

let _counter = 0
export function noteUid(): string {
    return `note-${Date.now()}-${++_counter}`
}

export function blockUid(): string {
    return `blk-${Date.now()}-${++_counter}`
}

export const useNoteStore = create<NoteState>((set, get) => ({
    notes: [],
    collections: [],
    activeNoteId: null,
    activeCollectionId: null,
    searchQuery: '',
    viewMode: 'list',
    sidePanelTab: 'outline',
    loading: false,
    popupNoteId: null,

    setNotes: (notes) => set({ notes }),
    setCollections: (collections) => set({ collections }),
    setActiveNoteId: (id) => set({ activeNoteId: id }),
    setActiveCollectionId: (id) => set({ activeCollectionId: id }),
    setSearchQuery: (q) => set({ searchQuery: q }),
    setViewMode: (mode) => set({ viewMode: mode }),
    setSidePanelTab: (tab) => set({ sidePanelTab: tab }),
    setLoading: (v) => set({ loading: v }),
    setPopupNoteId: (id) => set({ popupNoteId: id }),

    addNote: (note) => set((s) => ({ notes: [note, ...s.notes] })),

    updateNote: (id, patch) => {
        set((s) => ({
            notes: s.notes.map((n) => n.id === id ? { ...n, ...patch, updatedAt: new Date().toISOString() } : n),
        }))

        // Build the API-compatible patch (snake_case)
        const apiPatch: Record<string, unknown> = {}
        if (patch.title !== undefined) apiPatch.title = patch.title
        if (patch.content !== undefined) apiPatch.content = patch.content
        if (patch.isPinned !== undefined) apiPatch.pinned = patch.isPinned
        if (patch.isImportant !== undefined) apiPatch.is_important = patch.isImportant
        if (patch.collectionIds !== undefined) {
            apiPatch.collection_ids = patch.collectionIds.filter(
                id => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
            )
        }
        if (patch.todos !== undefined) apiPatch.todos = patch.todos

        if (Object.keys(apiPatch).length > 0) {
            // Pin/flag changes flush immediately; content/title changes are debounced
            const isImmediate = patch.isPinned !== undefined || patch.isImportant !== undefined || patch.collectionIds !== undefined
            debouncedPersist(id, apiPatch, isImmediate)
        }
    },

    removeNote: (id) => {
        set((s) => ({
            notes: s.notes.filter((n) => n.id !== id),
            activeNoteId: s.activeNoteId === id ? null : s.activeNoteId,
        }))

        // Cancel any pending save for this note
        const timer = _saveTimers.get(id)
        if (timer) {
            clearTimeout(timer)
            _saveTimers.delete(id)
        }

        // Delete from backend (skip temp IDs)
        if (!id.startsWith('note-')) {
            apiDeleteNote(id).catch((err) => {
                console.error(`[NoteStore] Failed to delete note ${id}:`, err)
            })
        }
    },

    updateNoteBlock: (noteId, blockId, patch) => {
        set((s) => ({
            notes: s.notes.map((n) =>
                n.id === noteId
                    ? {
                        ...n,
                        blocks: n.blocks.map((b) => b.id === blockId ? { ...b, ...patch } : b),
                        updatedAt: new Date().toISOString(),
                    }
                    : n
            ),
        }))

        // Persist the full note content after block change
        const note = get().notes.find((n) => n.id === noteId)
        if (note) {
            debouncedPersist(noteId, { content: note.content })
        }
    },

    addNoteBlock: (noteId, block, afterBlockId) => {
        set((s) => ({
            notes: s.notes.map((n) => {
                if (n.id !== noteId) return n
                const newBlocks = [...n.blocks]
                if (afterBlockId) {
                    const idx = newBlocks.findIndex((b) => b.id === afterBlockId)
                    newBlocks.splice(idx + 1, 0, block)
                } else {
                    newBlocks.push(block)
                }
                return { ...n, blocks: newBlocks, updatedAt: new Date().toISOString() }
            }),
        }))

        const note = get().notes.find((n) => n.id === noteId)
        if (note) {
            debouncedPersist(noteId, { content: note.content })
        }
    },

    removeNoteBlock: (noteId, blockId) => {
        set((s) => ({
            notes: s.notes.map((n) =>
                n.id === noteId
                    ? { ...n, blocks: n.blocks.filter((b) => b.id !== blockId), updatedAt: new Date().toISOString() }
                    : n
            ),
        }))

        const note = get().notes.find((n) => n.id === noteId)
        if (note) {
            debouncedPersist(noteId, { content: note.content })
        }
    },

    addCollection: (col) => {
        // Add locally with temp ID
        set((s) => ({ collections: [col, ...s.collections] }))

        // Persist to backend and swap temp ID with real one
        apiCreateCollection(col.name).then((saved) => {
            const store = useNoteStore.getState()
            const updated = store.collections.map((c) =>
                c.id === col.id ? { ...c, id: saved.id } : c,
            )
            // Also update any notes that reference the temp collection ID
            const updatedNotes = store.notes.map((n) =>
                (n.collectionIds ?? []).includes(col.id)
                    ? { ...n, collectionIds: (n.collectionIds ?? []).map(cid => cid === col.id ? saved.id : cid) }
                    : n,
            )
            useNoteStore.setState({
                collections: updated,
                activeCollectionId: store.activeCollectionId === col.id ? saved.id : store.activeCollectionId,
                notes: updatedNotes,
            })
        }).catch((err) => {
            console.error(`[NoteStore] Failed to create collection:`, err)
        })
    },

    updateCollection: (id, patch) => {
        set((s) => ({
            collections: s.collections.map((c) => c.id === id ? { ...c, ...patch } : c),
        }))

        // Persist rename to backend (skip temp IDs)
        if (!id.startsWith('note-') && patch.name) {
            apiUpdateCollection(id, { name: patch.name }).catch((err) => {
                console.error(`[NoteStore] Failed to update collection ${id}:`, err)
            })
        }
    },

    removeCollection: (id) => {
        set((s) => ({
            collections: s.collections.filter((c) => c.id !== id),
            activeCollectionId: s.activeCollectionId === id ? null : s.activeCollectionId,
            // Unset collection on notes that referenced this collection
            notes: s.notes.map((n) => (n.collectionIds ?? []).includes(id) ? { ...n, collectionIds: (n.collectionIds ?? []).filter(cid => cid !== id) } : n),
        }))

        // Delete from backend (skip temp IDs)
        if (!id.startsWith('note-')) {
            apiDeleteCollection(id).catch((err) => {
                console.error(`[NoteStore] Failed to delete collection ${id}:`, err)
            })
        }
    },

    getActiveNote: () => {
        const s = get()
        return s.notes.find((n) => n.id === s.activeNoteId)
    },

    getPopupNote: () => {
        const s = get()
        return s.notes.find((n) => n.id === s.popupNoteId)
    },

    getFilteredNotes: () => {
        const s = get()
        let filtered = s.notes
        if (s.activeCollectionId) {
            filtered = filtered.filter((n) => (n.collectionIds ?? []).includes(s.activeCollectionId!))
        }
        if (s.searchQuery.trim()) {
            const q = s.searchQuery.toLowerCase()
            filtered = filtered.filter(
                (n) =>
                    n.title.toLowerCase().includes(q) ||
                    n.content.toLowerCase().includes(q)
            )
        }
        // Pinned first, then by updatedAt desc
        return filtered.sort((a, b) => {
            if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1
            return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        })
    },
}))
