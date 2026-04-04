"use client"

import React, { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Layers,
  Loader2,
  Plus,
  Trash2,
  X,
  Target,
  CheckCircle2,
  Flame,
} from 'lucide-react'
import { useFlashcardStore } from '@/features/flashcards/store'
import { toast } from '@/shared/hooks/use-toast'
import { StatBox } from './StatBox'

export function DecksView() {
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
