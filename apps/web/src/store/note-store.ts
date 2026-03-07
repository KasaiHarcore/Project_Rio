import { create } from 'zustand'

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
    collectionId?: string
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

    // Note CRUD (local state)
    addNote: (note: Note) => void
    updateNote: (id: string, patch: Partial<Note>) => void
    removeNote: (id: string) => void
    updateNoteBlock: (noteId: string, blockId: string, patch: Partial<NoteBlock>) => void
    addNoteBlock: (noteId: string, block: NoteBlock, afterBlockId?: string) => void
    removeNoteBlock: (noteId: string, blockId: string) => void

    // Collection CRUD (local state)
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

    updateNote: (id, patch) => set((s) => ({
        notes: s.notes.map((n) => n.id === id ? { ...n, ...patch, updatedAt: new Date().toISOString() } : n),
    })),

    removeNote: (id) => set((s) => ({
        notes: s.notes.filter((n) => n.id !== id),
        activeNoteId: s.activeNoteId === id ? null : s.activeNoteId,
    })),

    updateNoteBlock: (noteId, blockId, patch) => set((s) => ({
        notes: s.notes.map((n) =>
            n.id === noteId
                ? {
                    ...n,
                    blocks: n.blocks.map((b) => b.id === blockId ? { ...b, ...patch } : b),
                    updatedAt: new Date().toISOString(),
                }
                : n
        ),
    })),

    addNoteBlock: (noteId, block, afterBlockId) => set((s) => ({
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
    })),

    removeNoteBlock: (noteId, blockId) => set((s) => ({
        notes: s.notes.map((n) =>
            n.id === noteId
                ? { ...n, blocks: n.blocks.filter((b) => b.id !== blockId), updatedAt: new Date().toISOString() }
                : n
        ),
    })),

    addCollection: (col) => set((s) => ({ collections: [col, ...s.collections] })),

    updateCollection: (id, patch) => set((s) => ({
        collections: s.collections.map((c) => c.id === id ? { ...c, ...patch } : c),
    })),

    removeCollection: (id) => set((s) => ({
        collections: s.collections.filter((c) => c.id !== id),
        activeCollectionId: s.activeCollectionId === id ? null : s.activeCollectionId,
        // Unset collection on notes that referenced this collection
        notes: s.notes.map((n) => n.collectionId === id ? { ...n, collectionId: undefined } : n),
    })),

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
            filtered = filtered.filter((n) => n.collectionId === s.activeCollectionId)
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
