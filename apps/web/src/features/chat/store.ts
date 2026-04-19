import { create } from 'zustand'
import { apiGetThreadMemories } from '@/features/chat/api'

/* ─── Types ──────────────────────────────────────────────────────── */

export type SidebarTab = 'agents' | 'workspace' | 'memory'

/** A logic bubble shown in the Agents tab — represents agent thinking/decisions */
export interface LogicEntry {
  id: string
  timestamp: number
  /** Short title like "Routing to RAG" or "Evaluating query" */
  title: string
  /** Longer explanation (can be multi-line) */
  detail?: string
  /** Severity / type for styling */
  kind: 'thinking' | 'decision' | 'tool-call' | 'info'
}


/** A sticky note the agent (or user) creates */
export interface StickyNote {
  id: string
  timestamp: number
  content: string
  /** If it contains TODO items, they're parsed out */
  todos?: { text: string; done: boolean }[]
  pinned: boolean
  /** Who created it */
  author: 'agent' | 'user'
  /** Database ID for persisted notes (UUID from backend). When present, DELETE calls go to the API. */
  dbId?: string
}

/** A file/document attached to the workspace context */
export interface WorkspaceFile {
  id: string
  /** Display name — can be a filename or short label */
  name: string
  /** Longer path or description */
  path: string
  /** File type for icon selection */
  type: 'code' | 'document' | 'data' | 'image' | 'other'
  addedAt: number
  /** If backed by a persisted artifact, its DB ID */
  artifactId?: string
  /** Artifact version number */
  artifactVersion?: number
  /** Cached file content for chunking (Phase 4) */
  content?: string
  /** Parsed code chunks (Phase 4) */
  chunks?: Array<{ name: string; kind: string; startLine: number; endLine: number; content: string }>
  /** File tree string (Phase 4) */
  fileTree?: string
}

/** A search result / retrieved reference */
export interface SearchReference {
  id: string
  timestamp: number
  source: 'rag' | 'web' | 'sql' | 'file'
  title: string
  snippet: string
  url?: string
}

/**
 * Structured web/doc source cited by an assistant turn. Rendered as a
 * rich preview card inside the tree view's DetailPanel (Messenger-style
 * link unfurl for web, document-thumbnail card for RAG / KB hits).
 *
 * Populated today by mock synthesis from logic entries; in a follow-up
 * phase the backend will emit a `source` SSE event with this shape
 * directly so we can drop the derivation layer.
 */
export interface WebSource {
  kind: 'web'
  /** Canonical URL — used as card anchor and for domain display. */
  url: string
  /** og:title — falls back to URL host when missing. */
  title: string
  /** og:description / meta description. */
  snippet?: string
  /** og:image hero. Absolute URL. */
  ogImage?: string
  /** Favicon URL. Absolute. */
  favicon?: string
  /** og:site_name or domain. */
  siteName?: string
  /** Time the citation was captured, ms since epoch. */
  timestamp: number
}

export interface DocSource {
  kind: 'doc'
  /** Document filename shown in the footer chip. */
  filename: string
  /** Optional display title (often same as filename without ext). */
  title?: string
  /** Data URL or blob URL for the thumbnail preview. */
  thumbnailUrl?: string
  /** Excerpt rendered inside the card body when no thumbnail is available. */
  excerpt?: string
  /** Page / section anchor within the document. */
  page?: number
  /** Origin — typically the knowledge-base / RAG worker name. */
  source?: string
  /** Captured at. */
  timestamp: number
}

export type MessageSource = WebSource | DocSource

/** A memory entry the agent writes or the user edits */
export interface MemoryEntry {
  id: string
  timestamp: number
  content: string
  /** Who wrote it — only 'agent' normally, but user can also add */
  author: 'agent' | 'user'
  /** Optional category tag for grouping */
  tag?: string
}

/* ─── Support State (Layer 1A) ──────────────────────────────────── */

export interface SupportAssessment {
  currentStage: string | null
  primaryGoal: string | null
  currentFriction: string | null
}

export interface SupportIntervention {
  intervention: string | null
  reasoning: string | null
}

/* ─── Store ──────────────────────────────────────────────────────── */

interface SidebarState {
  activeTab: SidebarTab

  /* Agents tab */
  logicEntries: LogicEntry[]
  stickyNotes: StickyNote[]

  /* Support state (Layer 1A) */
  supportAssessment: SupportAssessment | null
  supportIntervention: SupportIntervention | null
  supportNextStep: string | null

  /* Contextual notes (resurfaced from existing notes) */
  contextualNotes: Array<{ id: string; title: string; snippet: string; score: number; created_at: string }>

  /* Workspace tab */
  workspaceFiles: WorkspaceFile[]
  searchReferences: SearchReference[]

  /* Memory tab */
  memoryEntries: MemoryEntry[]
  persistedMemories: MemoryEntry[]
  memoriesLoading: boolean

  /**
   * Structured sources attached to an assistant message, keyed by its UIMessage id.
   * Populated by the transport when a `source` SSE event fires; read by the tree
   * view's DetailPanel to render rich preview cards.
   */
  messageSources: Record<string, MessageSource[]>

  /**
   * Sources for the in-flight assistant stream. The AI SDK assigns a
   * client-generated id to the streaming assistant message, but the
   * backend persists with its OWN UUID — those ids do not match until
   * the next page reload re-fetches the message list. Until then, the
   * DetailPanel falls back to this slot when the selected node is the
   * latest assistant turn.
   */
  liveAssistantSources: MessageSource[]

  /* ── Actions ── */
  setActiveTab: (tab: SidebarTab) => void

  // Logic
  addLogicEntry: (entry: Omit<LogicEntry, 'id' | 'timestamp'>) => void
  clearLogicEntries: () => void

  // Support state (Layer 1A)
  setSupportAssessment: (assessment: SupportAssessment) => void
  setSupportIntervention: (intervention: SupportIntervention) => void
  setSupportNextStep: (nextStep: string | null) => void

  // Contextual Notes
  setContextualNotes: (notes: SidebarState['contextualNotes']) => void
  clearContextualNotes: () => void

  // Sticky Notes
  addStickyNote: (note: Omit<StickyNote, 'id' | 'timestamp' | 'pinned'>) => void
  removeStickyNote: (id: string) => void
  removeStickyNoteByDbId: (dbId: string) => void
  updateStickyNoteByDbId: (dbId: string, patch: Partial<Pick<StickyNote, 'content' | 'todos'>>) => void
  toggleStickyPin: (id: string) => void
  toggleStickyTodo: (noteId: string, todoIndex: number) => void

  // Workspace Files
  addWorkspaceFile: (file: Omit<WorkspaceFile, 'id' | 'addedAt'>) => void
  addWorkspaceFileFromArtifact: (artifact: { id: string; name: string; type: string; version: number; content: string }) => void
  setFileChunks: (fileId: string, chunks: WorkspaceFile['chunks'], fileTree: string, content: string) => void
  removeWorkspaceFile: (id: string) => void
  clearWorkspaceFiles: () => void

  // Search References
  addSearchReference: (ref: Omit<SearchReference, 'id' | 'timestamp'>) => void
  removeSearchReference: (id: string) => void
  clearSearchReferences: () => void

  // Memory
  addMemoryEntry: (entry: Omit<MemoryEntry, 'id' | 'timestamp'>) => void
  removeMemoryEntry: (id: string) => void
  clearMemoryEntries: () => void
  fetchThreadMemories: (threadId: string) => Promise<void>

  // Message sources
  setMessageSources: (messageId: string, sources: MessageSource[]) => void
  appendMessageSource: (messageId: string, source: MessageSource) => void
  clearMessageSources: () => void

  // Live assistant sources (in-flight stream)
  setLiveAssistantSources: (sources: MessageSource[]) => void
  appendLiveAssistantSource: (source: MessageSource) => void
  clearLiveAssistantSources: () => void

  resetSession: () => void
}

let _counter = 0
function uid() { return `sb_${Date.now()}_${++_counter}` }

// Tracks the latest fetchThreadMemories request so stale responses from
// rapid thread switches don't overwrite the correct thread's data.
let _memoryFetchId = 0

/* ─── Limits (prevent sidebar from growing unbounded) ──────────── */
const LIMITS = {
  LOGIC_ENTRIES:     50,
  STICKY_NOTES:      20,
  WORKSPACE_FILES:   15,
  SEARCH_REFERENCES: 30,
  MEMORY_ENTRIES:    30,
  /** Max characters for user-authored text (notes, memory) */
  TEXT_MAX_LENGTH:  500,
} as const

export { LIMITS as SIDEBAR_LIMITS }

export const useSidebarStore = create<SidebarState>((set) => ({
  activeTab: 'agents',

  logicEntries: [],
  stickyNotes: [],
  supportAssessment: null,
  supportIntervention: null,
  supportNextStep: null,
  contextualNotes: [],
  workspaceFiles: [],
  searchReferences: [],
  memoryEntries: [],
  persistedMemories: [],
  memoriesLoading: false,
  messageSources: {},
  liveAssistantSources: [],

  setActiveTab: (tab) => set({ activeTab: tab }),

  /* ── Logic ── */
  addLogicEntry: (entry) => set((s) => ({
    logicEntries: [...s.logicEntries.slice(-(LIMITS.LOGIC_ENTRIES - 1)), { ...entry, id: uid(), timestamp: Date.now() }],
  })),
  clearLogicEntries: () => set({ logicEntries: [] }),

  /* ── Contextual Notes ── */
  setContextualNotes: (notes) => set({ contextualNotes: notes }),
  clearContextualNotes: () => set({ contextualNotes: [] }),

  /* ── Support State (Layer 1A) ── */
  setSupportAssessment: (assessment) => set({ supportAssessment: assessment }),
  setSupportIntervention: (intervention) => set({ supportIntervention: intervention }),
  setSupportNextStep: (nextStep) => set({ supportNextStep: nextStep }),

  /* ── Sticky Notes ── */
  addStickyNote: (note) => set((s) => {
    const next = [{ ...note, id: uid(), timestamp: Date.now(), pinned: false }, ...s.stickyNotes]
    if (next.length > LIMITS.STICKY_NOTES) {
      const unpinnedIdx = [...next].reverse().findIndex((n) => !n.pinned)
      if (unpinnedIdx >= 0) next.splice(next.length - 1 - unpinnedIdx, 1)
      else next.pop()
    }
    return { stickyNotes: next }
  }),
  removeStickyNote: (id) => set((s) => ({
    stickyNotes: s.stickyNotes.filter((n) => n.id !== id),
  })),
  removeStickyNoteByDbId: (dbId) => set((s) => ({
    stickyNotes: s.stickyNotes.filter((n) => n.dbId !== dbId),
  })),
  updateStickyNoteByDbId: (dbId, patch) => set((s) => ({
    stickyNotes: s.stickyNotes.map((n) =>
      n.dbId === dbId ? { ...n, ...patch } : n
    ),
  })),
  toggleStickyPin: (id) => set((s) => ({
    stickyNotes: s.stickyNotes.map((n) => n.id === id ? { ...n, pinned: !n.pinned } : n),
  })),
  toggleStickyTodo: (noteId, todoIndex) => set((s) => ({
    stickyNotes: s.stickyNotes.map((n) => {
      if (n.id !== noteId || !n.todos) return n
      const todos = n.todos.map((t, i) => i === todoIndex ? { ...t, done: !t.done } : t)
      return { ...n, todos }
    }),
  })),

  /* ── Workspace Files ── */
  addWorkspaceFile: (file) => set((s) => {
    // Prevent duplicates by path or artifactId
    if (s.workspaceFiles.some((f) => f.path === file.path)) return s
    if (file.artifactId && s.workspaceFiles.some((f) => f.artifactId === file.artifactId)) return s
    if (s.workspaceFiles.length >= LIMITS.WORKSPACE_FILES) return s   // hard cap
    return { workspaceFiles: [...s.workspaceFiles, { ...file, id: uid(), addedAt: Date.now() }] }
  }),
  addWorkspaceFileFromArtifact: (artifact) => set((s) => {
    if (s.workspaceFiles.some((f) => f.artifactId === artifact.id)) return s
    if (s.workspaceFiles.length >= LIMITS.WORKSPACE_FILES) return s
    const wsType = artifact.type === 'document' ? 'document' : artifact.type === 'data' ? 'data' : artifact.type === 'image' ? 'image' : 'code'
    return {
      workspaceFiles: [...s.workspaceFiles, {
        id: uid(),
        name: artifact.name,
        path: `artifact://${artifact.id}`,
        type: wsType as WorkspaceFile['type'],
        addedAt: Date.now(),
        artifactId: artifact.id,
        artifactVersion: artifact.version,
        content: artifact.content,
      }],
    }
  }),
  setFileChunks: (fileId, chunks, fileTree, content) => set((s) => ({
    workspaceFiles: s.workspaceFiles.map((f) =>
      f.id === fileId ? { ...f, chunks, fileTree, content } : f
    ),
  })),
  removeWorkspaceFile: (id) => set((s) => ({
    workspaceFiles: s.workspaceFiles.filter((f) => f.id !== id),
  })),
  clearWorkspaceFiles: () => set({ workspaceFiles: [] }),

  /* ── Search References ── */
  addSearchReference: (ref) => set((s) => ({
    searchReferences: [...s.searchReferences.slice(-(LIMITS.SEARCH_REFERENCES - 1)), { ...ref, id: uid(), timestamp: Date.now() }],
  })),
  removeSearchReference: (id) => set((s) => ({
    searchReferences: s.searchReferences.filter((r) => r.id !== id),
  })),
  clearSearchReferences: () => set({ searchReferences: [] }),

  /* ── Memory ── */
  addMemoryEntry: (entry) => set((s) => ({
    memoryEntries: [...s.memoryEntries.slice(-(LIMITS.MEMORY_ENTRIES - 1)), { ...entry, id: uid(), timestamp: Date.now() }],
  })),
  removeMemoryEntry: (id) => set((s) => ({
    memoryEntries: s.memoryEntries.filter((e) => e.id !== id),
  })),
  clearMemoryEntries: () => set({ memoryEntries: [] }),
  fetchThreadMemories: async (threadId: string) => {
    const fetchId = ++_memoryFetchId
    set({ memoriesLoading: true })
    try {
      const res = await apiGetThreadMemories(threadId)
      // Discard if a newer request was initiated while we were waiting
      if (fetchId !== _memoryFetchId) return
      const mapped: MemoryEntry[] = res.memories.map((m) => ({
        id: `persisted_${m.key}`,
        timestamp: m.created_at ? new Date(m.created_at).getTime() : 0,
        content: m.text,
        author: 'agent' as const,
        tag: m.memory_type || m.mode || undefined,
      }))
      set({ persistedMemories: mapped })
    } catch {
      if (fetchId !== _memoryFetchId) return
      set({ persistedMemories: [] })
    } finally {
      if (fetchId === _memoryFetchId) {
        set({ memoriesLoading: false })
      }
    }
  },

  /* ── Message Sources ── */
  setMessageSources: (messageId, sources) => set((s) => ({
    messageSources: { ...s.messageSources, [messageId]: sources },
  })),
  appendMessageSource: (messageId, source) => set((s) => ({
    messageSources: {
      ...s.messageSources,
      [messageId]: [...(s.messageSources[messageId] ?? []), source],
    },
  })),
  clearMessageSources: () => set({ messageSources: {} }),

  /* ── Live Assistant Sources ── */
  setLiveAssistantSources: (sources) => set({ liveAssistantSources: sources }),
  appendLiveAssistantSource: (source) => set((s) => ({
    liveAssistantSources: [...s.liveAssistantSources, source],
  })),
  clearLiveAssistantSources: () => set({ liveAssistantSources: [] }),

  /* ── Session Reset ── */
  resetSession: () => set({
    logicEntries: [],
    stickyNotes: [],
    supportAssessment: null,
    supportIntervention: null,
    supportNextStep: null,
    contextualNotes: [],
    searchReferences: [],
    memoryEntries: [],
    persistedMemories: [],
    memoriesLoading: false,
    messageSources: {},
    liveAssistantSources: [],
    // Keep workspaceFiles — those are project-level, not session-level
  }),
}))
