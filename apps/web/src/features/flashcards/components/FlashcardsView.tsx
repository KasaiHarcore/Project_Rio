"use client"

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart3,
  BookOpen,
  ChevronRight,
  Layers,
  Loader2,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  X,
  Zap,
  Flame,
  Target,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useFlashcardStore, type FlashcardView } from '@/features/flashcards/store'
import { toast } from '@/shared/hooks/use-toast'
import { apiListNotes, type NoteRecord } from '@/features/notes/api'

/* ═══════════════════════════════════════════════════════════════════
 * FlashcardsView
 * ═══════════════════════════════════════════════════════════════════ */

// Simplified 3-button rating — maps to SM-2 quality values
const RATING_BUTTONS = [
  { quality: 1, label: 'Again', key: '1', color: 'bg-red-500 hover:bg-red-600' },
  { quality: 3, label: 'Good', key: '2', color: 'bg-amber-500 hover:bg-amber-600' },
  { quality: 5, label: 'Easy', key: '3', color: 'bg-green-500 hover:bg-green-600' },
] as const

export function FlashcardsView() {
  const store = useFlashcardStore()

  /* ── Mount ── */
  useEffect(() => {
    store.fetchDecks()
    store.fetchStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <DashboardLayout>
      <PageTransition className="flex-1 flex flex-col overflow-hidden bg-[var(--page-bg)]">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 border-[var(--page-header-border)] bg-[var(--page-header-bg)]">
          <div className="absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent via-[var(--page-header-line)] to-transparent" />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  "bg-gradient-to-br from-rose-700 to-rose-900"
                )}
                style={{ boxShadow: '0 10px 15px -3px var(--page-icon-shadow)' }}
              >
                <Layers className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Flashcards</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">Spaced Repetition</p>
              </div>
            </div>
          </div>

          {/* View toggle (Decks / Stats) */}
          {store.view !== 'study' && (
            <div className="flex items-center gap-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-1">
              {(['decks', 'stats'] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => {
                    store.setView(v)
                    if (v === 'decks') store.setActiveDeck(null)
                  }}
                  className={cn(
                    'px-4 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all',
                    (store.view === v || (v === 'decks' && (store.view === 'cards')))
                      ? 'bg-[var(--primary)] text-white'
                      : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
                  )}
                >
                  {v === 'decks' ? 'Decks' : 'Stats'}
                </button>
              ))}
            </div>
          )}
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          <AnimatePresence mode="wait">
            {store.view === 'decks' && <DecksView key="decks" />}
            {store.view === 'cards' && <CardsView key="cards" />}
            {store.view === 'study' && <StudyView key="study" />}
            {store.view === 'stats' && <StatsView key="stats" />}
          </AnimatePresence>
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * 1. Decks View
 * ═══════════════════════════════════════════════════════════════════ */

function DecksView() {
  const store = useFlashcardStore()
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return
    const deck = await store.createDeck(newName.trim(), newDesc.trim())
    if (deck) {
      toast({ title: 'Deck created', variant: 'success' })
      setNewName('')
      setNewDesc('')
      setShowCreate(false)
    } else {
      toast({ title: 'Failed to create deck', variant: 'error' })
    }
  }, [newName, newDesc, store])

  const handleDelete = useCallback(async (id: string) => {
    const ok = await store.deleteDeck(id)
    if (ok) toast({ title: 'Deck deleted' })
    else toast({ title: 'Failed to delete deck', variant: 'error' })
  }, [store])

  const handleStudy = useCallback(async (deckId: string) => {
    const started = await store.startStudySession(deckId)
    if (!started) toast({ title: 'No cards due for review', variant: 'warning' })
  }, [store])

  const handleViewCards = useCallback((deckId: string) => {
    store.setActiveDeck(deckId)
    store.setView('cards')
    store.fetchCards(deckId)
  }, [store])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {/* Stats bar */}
      {store.stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatBox icon={<Layers className="h-4 w-4" />} label="Total Cards" value={store.stats.total_cards} color="from-rose-500 to-rose-700" />
          <StatBox icon={<Target className="h-4 w-4" />} label="Due Today" value={store.stats.due_today} highlight={store.stats.due_today > 0} color="from-amber-500 to-amber-700" />
          <StatBox icon={<CheckCircle2 className="h-4 w-4" />} label="Accuracy" value={`${Math.round(store.stats.accuracy_rate * 100)}%`} color="from-emerald-500 to-emerald-700" />
          <StatBox icon={<Flame className="h-4 w-4" />} label="Streak" value={store.stats.longest_streak} color="from-orange-500 to-orange-700" />
        </div>
      )}

      {/* Deck grid */}
      {store.loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {store.decks.map((deck) => (
            <div
              key={deck.id}
              className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-5 backdrop-blur-xl flex flex-col gap-3"
            >
              <div>
                <h3 className="text-lg font-bold text-foreground">{deck.name}</h3>
                {deck.description && (
                  <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{deck.description}</p>
                )}
              </div>

              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{deck.flashcard_count} cards</span>
                {deck.due_count > 0 && (
                  <span className="bg-[var(--primary)] text-white px-2 py-0.5 rounded-full text-xs font-medium">
                    {deck.due_count} due
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 mt-auto pt-2">
                {deck.due_count > 0 && (
                  <button
                    onClick={() => handleStudy(deck.id)}
                    className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
                  >
                    Study
                  </button>
                )}
                <button
                  onClick={() => handleViewCards(deck.id)}
                  className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg px-3 py-2 text-sm transition-colors"
                >
                  View Cards
                </button>
                <button
                  onClick={() => handleDelete(deck.id)}
                  className="ml-auto text-muted-foreground hover:text-red-400 hover:bg-white/5 rounded-lg p-2 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}

          {/* Create deck toggle */}
          {!showCreate && (
            <button
              onClick={() => setShowCreate(true)}
              className="border border-dashed border-[var(--card-border)] rounded-xl p-5 flex flex-col items-center justify-center gap-2 text-muted-foreground hover:text-foreground hover:border-[var(--primary)] transition-colors min-h-[160px]"
            >
              <Plus className="h-6 w-6" />
              <span className="text-sm font-medium">Create Deck</span>
            </button>
          )}
        </div>
      )}

      {/* Create deck form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">New Deck</h3>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Deck name"
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] flex-1"
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
                <input
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Description (optional)"
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] flex-1"
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
                <button
                  onClick={handleCreate}
                  disabled={!newName.trim()}
                  className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
                >
                  Create
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!store.loading && store.decks.length === 0 && !showCreate && (
        <div className="text-center py-20 text-muted-foreground">
          <Layers className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No decks yet. Create one to get started.</p>
        </div>
      )}
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * 2. Cards View
 * ═══════════════════════════════════════════════════════════════════ */

function CardsView() {
  const store = useFlashcardStore()
  const [showAddCard, setShowAddCard] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [front, setFront] = useState('')
  const [back, setBack] = useState('')
  const [tags, setTags] = useState('')
  const [maxCards, setMaxCards] = useState(10)

  // Note picker state for generate
  const [notes, setNotes] = useState<NoteRecord[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [selectedNoteId, setSelectedNoteId] = useState('')

  // Card edit state
  const [editCardId, setEditCardId] = useState<string | null>(null)
  const [editFront, setEditFront] = useState('')
  const [editBack, setEditBack] = useState('')
  const [editTags, setEditTags] = useState('')

  const activeDeck = store.decks.find((d) => d.id === store.activeDeckId)

  const goBackToDecks = useCallback(() => {
    store.setActiveDeck(null)
    store.setView('decks')
  }, [store])

  const handleAddCard = useCallback(async () => {
    if (!front.trim() || !back.trim() || !store.activeDeckId) return
    const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean)
    const card = await store.createCard({
      deck_id: store.activeDeckId,
      front: front.trim(),
      back: back.trim(),
      tags: tagList.length > 0 ? tagList : undefined,
    })
    if (card) {
      toast({ title: 'Card added', variant: 'success' })
      setFront('')
      setBack('')
      setTags('')
      setShowAddCard(false)
    } else {
      toast({ title: 'Failed to add card', variant: 'error' })
    }
  }, [front, back, tags, store])

  // Fetch notes when generate panel opens
  useEffect(() => {
    if (!showGenerate) return
    setNotesLoading(true)
    apiListNotes().then((data) => setNotes(data)).finally(() => setNotesLoading(false))
  }, [showGenerate])

  const handleGenerate = useCallback(async () => {
    if (!selectedNoteId || !store.activeDeckId) return
    const cards = await store.generateFromNote(selectedNoteId, store.activeDeckId, maxCards)
    if (cards.length > 0) {
      toast({ title: `Generated ${cards.length} cards`, variant: 'success' })
      setSelectedNoteId('')
      setMaxCards(10)
      setShowGenerate(false)
    } else {
      toast({ title: 'No cards generated. The note may be empty or the AI could not extract concepts.', variant: 'warning' })
    }
  }, [selectedNoteId, maxCards, store])

  const handleEditStart = useCallback((card: { id: string; front: string; back: string; tags: string[] }) => {
    setEditCardId(card.id)
    setEditFront(card.front)
    setEditBack(card.back)
    setEditTags(card.tags.join(', '))
  }, [])

  const handleEditSave = useCallback(async () => {
    if (!editCardId) return
    const tagList = editTags.split(',').map((t) => t.trim()).filter(Boolean)
    const updated = await store.updateCard(editCardId, {
      front: editFront.trim(),
      back: editBack.trim(),
      tags: tagList,
    })
    if (updated) {
      toast({ title: 'Card updated', variant: 'success' })
      setEditCardId(null)
    } else {
      toast({ title: 'Failed to update card', variant: 'error' })
    }
  }, [editCardId, editFront, editBack, editTags, store])

  const handleToggleSuspend = useCallback(async (id: string, suspended: boolean) => {
    const updated = await store.updateCard(id, { is_suspended: !suspended })
    if (updated) {
      toast({ title: suspended ? 'Card resumed' : 'Card suspended' })
    }
  }, [store])

  const handleDeleteCard = useCallback(async (id: string) => {
    const ok = await store.deleteCard(id)
    if (ok) toast({ title: 'Card deleted' })
    else toast({ title: 'Failed to delete card', variant: 'error' })
  }, [store])

  const handleStudyDeck = useCallback(async () => {
    if (!store.activeDeckId) return
    const started = await store.startStudySession(store.activeDeckId)
    if (!started) toast({ title: 'No cards due for review', variant: 'warning' })
  }, [store])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
        <button onClick={goBackToDecks} className="hover:text-foreground transition-colors">
          Decks
        </button>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground font-medium">{activeDeck?.name ?? 'Unknown'}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h2 className="text-lg font-bold text-foreground">{activeDeck?.name}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleStudyDeck}
            className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Study This Deck
          </button>
          <button
            onClick={() => { setShowAddCard((p) => !p); setShowGenerate(false) }}
            className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            <Plus className="h-4 w-4 inline mr-1" />
            Add Card
          </button>
          <button
            onClick={() => { setShowGenerate((p) => !p); setShowAddCard(false) }}
            className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            <Sparkles className="h-4 w-4 inline mr-1" />
            Generate from Note
          </button>
        </div>
      </div>

      {/* Add Card form */}
      <AnimatePresence>
        {showAddCard && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mb-4 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">New Card</h3>
                <button onClick={() => setShowAddCard(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="flex flex-col gap-3">
                <textarea
                  value={front}
                  onChange={(e) => setFront(e.target.value)}
                  placeholder="Front (question)"
                  rows={3}
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
                />
                <textarea
                  value={back}
                  onChange={(e) => setBack(e.target.value)}
                  placeholder="Back (answer)"
                  rows={3}
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
                />
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="Tags (comma-separated, optional)"
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                />
                <div className="flex justify-end">
                  <button
                    onClick={handleAddCard}
                    disabled={!front.trim() || !back.trim()}
                    className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
                  >
                    Add Card
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generate from Note form */}
      <AnimatePresence>
        {showGenerate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mb-4 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">Generate from Note</h3>
                <button onClick={() => setShowGenerate(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="flex flex-col sm:flex-row gap-3">
                {notesLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground flex-1">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading notes…
                  </div>
                ) : notes.length === 0 ? (
                  <p className="text-sm text-muted-foreground flex-1">No notes found. Create a note first.</p>
                ) : (
                  <select
                    value={selectedNoteId}
                    onChange={(e) => setSelectedNoteId(e.target.value)}
                    className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] flex-1 text-foreground"
                  >
                    <option value="">Select a note…</option>
                    {notes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.title || 'Untitled note'} — {new Date(n.updated_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                )}
                <input
                  type="number"
                  value={maxCards}
                  onChange={(e) => setMaxCards(Number(e.target.value) || 10)}
                  min={1}
                  max={50}
                  placeholder="Max cards"
                  className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] w-28"
                />
                <button
                  onClick={handleGenerate}
                  disabled={!selectedNoteId || store.generating}
                  className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center gap-2"
                >
                  {store.generating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Generate
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Card list */}
      {store.loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : store.cards.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No cards in this deck yet.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {store.cards.map((card) => (
            <div
              key={card.id}
              className={cn(
                "bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-4 backdrop-blur-xl",
                card.is_suspended && "opacity-50",
              )}
            >
              {editCardId === card.id ? (
                /* ── Inline edit form ── */
                <div className="flex flex-col gap-3">
                  <textarea
                    value={editFront}
                    onChange={(e) => setEditFront(e.target.value)}
                    rows={2}
                    className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
                    placeholder="Front (question)"
                  />
                  <textarea
                    value={editBack}
                    onChange={(e) => setEditBack(e.target.value)}
                    rows={2}
                    className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
                    placeholder="Back (answer)"
                  />
                  <input
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    placeholder="Tags (comma-separated)"
                    className="bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditCardId(null)}
                      className="text-muted-foreground hover:text-foreground px-3 py-1.5 text-sm transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleEditSave}
                      disabled={!editFront.trim() || !editBack.trim()}
                      className="bg-[var(--primary)] text-white rounded-lg px-4 py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                /* ── Card display ── */
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      {card.front.length > 100 ? card.front.slice(0, 100) + '…' : card.front}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {card.back.length > 100 ? card.back.slice(0, 100) + '…' : card.back}
                    </p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className={cn(
                        'text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full',
                        card.source === 'agent'
                          ? 'bg-purple-500/20 text-purple-300'
                          : 'bg-blue-500/20 text-blue-300',
                      )}>
                        {card.source}
                      </span>
                      {card.is_suspended && (
                        <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-500/20 text-slate-400">
                          suspended
                        </span>
                      )}
                      {card.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-muted-foreground"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleEditStart(card)}
                      title="Edit card"
                      className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg p-2 transition-colors"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleToggleSuspend(card.id, card.is_suspended)}
                      title={card.is_suspended ? 'Resume card' : 'Suspend card'}
                      className="text-muted-foreground hover:text-amber-400 hover:bg-white/5 rounded-lg p-2 transition-colors"
                    >
                      {card.is_suspended
                        ? <PlayCircle className="h-4 w-4" />
                        : <PauseCircle className="h-4 w-4" />
                      }
                    </button>
                    <button
                      onClick={() => handleDeleteCard(card.id)}
                      title="Delete card"
                      className="text-muted-foreground hover:text-red-400 hover:bg-white/5 rounded-lg p-2 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * 3. Study View
 * ═══════════════════════════════════════════════════════════════════ */

function StudyView() {
  const store = useFlashcardStore()
  const session = store.reviewSession
  const [showAnswer, setShowAnswer] = useState(false)

  // Reset showAnswer when moving to next card
  useEffect(() => {
    setShowAnswer(false)
  }, [session?.currentIndex])

  // Keyboard shortcuts: Space = flip, 1/2/3 = rate
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault()
        if (!showAnswer) setShowAnswer(true)
      } else if (showAnswer) {
        if (e.key === '1') handleRate(1)
        else if (e.key === '2') handleRate(3)
        else if (e.key === '3') handleRate(5)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showAnswer, session?.currentIndex])

  if (!session) return null

  const isComplete = session.currentIndex >= session.cards.length
  const currentCard = isComplete ? null : session.cards[session.currentIndex]

  const handleRate = async (quality: number) => {
    if (!currentCard) return
    await store.submitReview(currentCard.id, quality)
    store.nextCard()
  }

  // Session summary
  if (isComplete) {
    const totalReviewed = session.results.length
    const correctCount = session.results.filter((r) => r.is_correct).length
    const accuracy = totalReviewed > 0 ? Math.round((correctCount / totalReviewed) * 100) : 0

    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2 }}
        className="flex flex-col items-center justify-center py-20"
      >
        <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-8 backdrop-blur-xl max-w-md w-full text-center">
          <CheckCircle2 className="h-12 w-12 mx-auto mb-4 text-green-500" />
          <h2 className="text-xl font-bold text-foreground mb-6">Session Complete</h2>

          <div className="grid grid-cols-3 gap-4 mb-8">
            <div>
              <p className="text-2xl font-bold text-foreground">{totalReviewed}</p>
              <p className="text-xs text-muted-foreground">Reviewed</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-500">{correctCount}</p>
              <p className="text-xs text-muted-foreground">Correct</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--primary)]">{accuracy}%</p>
              <p className="text-xs text-muted-foreground">Accuracy</p>
            </div>
          </div>

          <button
            onClick={() => store.endSession()}
            className="bg-[var(--primary)] text-white rounded-lg px-6 py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Back to Decks
          </button>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col items-center"
    >
      {/* Progress bar */}
      <div className="w-full max-w-2xl mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-foreground">
            {session.currentIndex + 1} / {session.cards.length}
          </span>
          <div className="flex items-center gap-2">
            {session.config.encouragement_style && (
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
                {session.config.encouragement_style}
              </span>
            )}
            {session.config.difficulty_bias && (
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
                {session.config.difficulty_bias}
              </span>
            )}
          </div>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--primary)] rounded-full transition-all duration-300"
            style={{ width: `${((session.currentIndex + 1) / session.cards.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Card */}
      {currentCard && (
        <div className="w-full max-w-2xl">
          <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-8 backdrop-blur-xl min-h-[300px] flex flex-col items-center justify-center text-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={showAnswer ? 'back' : 'front'}
                initial={{ opacity: 0, rotateX: -10 }}
                animate={{ opacity: 1, rotateX: 0 }}
                exit={{ opacity: 0, rotateX: 10 }}
                transition={{ duration: 0.2 }}
                className="w-full"
              >
                <p className="text-lg font-medium text-foreground whitespace-pre-wrap">
                  {currentCard.front}
                </p>

                {showAnswer && (
                  <div className="mt-6 pt-6 border-t border-[var(--card-border)]">
                    <p className="text-base text-muted-foreground whitespace-pre-wrap">
                      {currentCard.back}
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Actions */}
          <div className="mt-6">
            {!showAnswer ? (
              <div className="flex justify-center">
                <button
                  onClick={() => setShowAnswer(true)}
                  className="bg-[var(--primary)] text-white rounded-lg px-8 py-3 text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  Show Answer
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="flex justify-center gap-3">
                  {RATING_BUTTONS.map(({ quality, label, key, color }) => (
                    <button
                      key={quality}
                      onClick={() => handleRate(quality)}
                      className={cn(
                        color,
                        'text-white rounded-lg px-6 py-2.5 text-sm font-semibold transition-colors min-w-[80px]',
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Keyboard: <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">Space</kbd> flip &nbsp;
                  <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">1</kbd> again &nbsp;
                  <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">2</kbd> good &nbsp;
                  <kbd className="px-1 py-0.5 bg-white/10 rounded text-[10px]">3</kbd> easy
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * 4. Stats View
 * ═══════════════════════════════════════════════════════════════════ */

function StatsView() {
  const store = useFlashcardStore()

  useEffect(() => {
    store.fetchStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!store.stats) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2 }}
        className="flex items-center justify-center py-20"
      >
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </motion.div>
    )
  }

  const { stats } = store

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {/* Overall stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        <StatBox icon={<Layers className="h-4 w-4" />} label="Total Cards" value={stats.total_cards} color="from-rose-500 to-rose-700" />
        <StatBox icon={<Target className="h-4 w-4" />} label="Due Today" value={stats.due_today} highlight={stats.due_today > 0} color="from-amber-500 to-amber-700" />
        <StatBox icon={<Zap className="h-4 w-4" />} label="Reviewed Today" value={stats.reviewed_today} color="from-blue-500 to-blue-700" />
        <StatBox icon={<BarChart3 className="h-4 w-4" />} label="Accuracy" value={`${Math.round(stats.accuracy_rate * 100)}%`} color="from-emerald-500 to-emerald-700" />
        <StatBox icon={<Flame className="h-4 w-4" />} label="Longest Streak" value={stats.longest_streak} color="from-orange-500 to-orange-700" />
      </div>

      {/* Per-deck breakdown */}
      <h3 className="text-sm font-semibold text-foreground mb-4 uppercase tracking-wider">Per-Deck Breakdown</h3>
      {stats.decks.length === 0 ? (
        <p className="text-sm text-muted-foreground">No decks found.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {stats.decks.map((deck) => (
            <div
              key={deck.id}
              className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-2xl shadow-sm p-4 backdrop-blur-xl flex items-center justify-between"
            >
              <div>
                <h4 className="text-sm font-medium text-foreground">{deck.name}</h4>
                {deck.description && (
                  <p className="text-xs text-muted-foreground mt-0.5">{deck.description}</p>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>{deck.flashcard_count} cards</span>
                {deck.due_count > 0 ? (
                  <span className="bg-[var(--primary)] text-white px-2 py-0.5 rounded-full text-xs font-medium">
                    {deck.due_count} due
                  </span>
                ) : (
                  <span className="text-green-500 text-xs font-medium">All caught up</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
 * Shared Components
 * ═══════════════════════════════════════════════════════════════════ */

function StatBox({
  icon,
  label,
  value,
  highlight = false,
  color = 'from-slate-600 to-slate-700',
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  highlight?: boolean
  color?: string
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border p-5 shadow-sm bg-[var(--card-bg)] border-[var(--card-border)]">
      <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${color}`} />
      <p className={cn(
        'text-2xl font-black',
        highlight ? 'text-[var(--primary)]' : 'text-page-card-title',
      )}>
        {value}
      </p>
      <p className="text-[10px] font-bold tracking-wider text-page-muted uppercase">{label}</p>
    </div>
  )
}
