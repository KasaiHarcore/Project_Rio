"use client"

import React, { useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Layers,
  Loader2,
  Zap,
  Flame,
  Target,
} from 'lucide-react'
import { useFlashcardStore } from '@/features/flashcards/store'
import { StatBox } from './StatBox'

export function StatsView() {
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
