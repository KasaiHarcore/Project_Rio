"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2 } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useFlashcardStore } from '@/features/flashcards/store'

// Simplified 3-button rating — maps to SM-2 quality values
const RATING_BUTTONS = [
  { quality: 1, label: 'Again', key: '1', color: 'bg-red-500 hover:bg-red-600' },
  { quality: 3, label: 'Good', key: '2', color: 'bg-amber-500 hover:bg-amber-600' },
  { quality: 5, label: 'Easy', key: '3', color: 'bg-green-500 hover:bg-green-600' },
] as const

export function StudyView() {
  const store = useFlashcardStore()
  const session = store.reviewSession
  const [showAnswer, setShowAnswer] = useState(false)

  // Reset showAnswer when moving to next card
  useEffect(() => {
    setShowAnswer(false)
  }, [session?.currentIndex])

  // Keyboard shortcuts: Space = flip, 1/2/3 = rate
  // Inline rate logic to avoid stale closure over currentCard
  useEffect(() => {
    if (!session) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault()
        if (!showAnswer) setShowAnswer(true)
      } else if (showAnswer) {
        const card = session.currentIndex < session.cards.length ? session.cards[session.currentIndex] : null
        if (!card) return
        const rateAndNext = (q: number) => { store.submitReview(card.id, q).then(() => store.nextCard()) }
        if (e.key === '1') rateAndNext(1)
        else if (e.key === '2') rateAndNext(3)
        else if (e.key === '3') rateAndNext(5)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [showAnswer, session, store])

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
