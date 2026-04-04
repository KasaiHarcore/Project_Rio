"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BookOpen,
  ChevronRight,
  Loader2,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  X,
  PauseCircle,
  PlayCircle,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useFlashcardStore } from '@/features/flashcards/store'
import { toast } from '@/shared/hooks/use-toast'
import { apiListNotes, type NoteRecord } from '@/features/notes/api'

export function CardsView() {
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
                /* Inline edit form */
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
                /* Card display */
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
