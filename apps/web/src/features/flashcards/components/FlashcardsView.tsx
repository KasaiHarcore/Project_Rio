"use client"

import React, { useEffect } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { AnimatePresence } from 'framer-motion'
import { Layers } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useFlashcardStore } from '@/features/flashcards/store'
import { DecksView } from './DecksView'
import { CardsView } from './CardsView'
import { StudyView } from './StudyView'
import { StatsView } from './StatsView'

export function FlashcardsView() {
  const store = useFlashcardStore()

  /* Mount */
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
