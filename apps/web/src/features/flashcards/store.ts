import { create } from 'zustand'
import {
  apiListDecks, apiCreateDeck, apiDeleteDeck,
  apiListCards, apiCreateCard, apiUpdateCard, apiDeleteCard,
  apiGetDueCards, apiSubmitReview,
  apiGenerateFromNote, apiGetStats, apiGetAdaptiveSession,
} from './api'
import type { Deck, Flashcard, ReviewResult, FlashcardStats, AdaptiveSession } from './api'

export type FlashcardView = 'decks' | 'cards' | 'study' | 'stats'

interface ReviewSession {
  cards: Flashcard[]
  currentIndex: number
  config: AdaptiveSession['session_config']
  results: ReviewResult[]
  emotionalContext: Record<string, string>
}

interface FlashcardState {
  decks: Deck[]
  cards: Flashcard[]
  stats: FlashcardStats | null
  activeDeckId: string | null
  loading: boolean
  generating: boolean
  view: FlashcardView
  reviewSession: ReviewSession | null

  fetchDecks: () => Promise<void>
  createDeck: (name: string, description?: string) => Promise<Deck | null>
  deleteDeck: (id: string) => Promise<boolean>
  fetchCards: (deckId?: string) => Promise<void>
  createCard: (data: { deck_id: string; front: string; back: string; tags?: string[] }) => Promise<Flashcard | null>
  updateCard: (id: string, data: { front?: string; back?: string; tags?: string[]; is_suspended?: boolean }) => Promise<Flashcard | null>
  deleteCard: (id: string) => Promise<boolean>
  startStudySession: (deckId?: string) => Promise<boolean>
  submitReview: (cardId: string, quality: number) => Promise<ReviewResult | null>
  nextCard: () => void
  endSession: () => void
  generateFromNote: (noteId: string, deckId: string, maxCards?: number) => Promise<Flashcard[]>
  fetchStats: () => Promise<void>
  setActiveDeck: (id: string | null) => void
  setView: (view: FlashcardView) => void
}

export const useFlashcardStore = create<FlashcardState>((set, get) => ({
  decks: [],
  cards: [],
  stats: null,
  activeDeckId: null,
  loading: false,
  generating: false,
  view: 'decks',
  reviewSession: null,

  fetchDecks: async () => {
    set({ loading: true })
    try {
      const decks = await apiListDecks()
      set({ decks })
    } catch { /* ignore */ } finally {
      set({ loading: false })
    }
  },

  createDeck: async (name, description) => {
    try {
      const deck = await apiCreateDeck(name, description)
      set((s) => ({ decks: [deck, ...s.decks] }))
      return deck
    } catch { return null }
  },

  deleteDeck: async (id) => {
    try {
      await apiDeleteDeck(id)
      set((s) => ({
        decks: s.decks.filter((d) => d.id !== id),
        activeDeckId: s.activeDeckId === id ? null : s.activeDeckId,
      }))
      return true
    } catch { return false }
  },

  fetchCards: async (deckId) => {
    set({ loading: true })
    try {
      const cards = await apiListCards(deckId)
      set({ cards })
    } catch { /* ignore */ } finally {
      set({ loading: false })
    }
  },

  createCard: async (data) => {
    try {
      const card = await apiCreateCard(data)
      set((s) => ({ cards: [card, ...s.cards] }))
      return card
    } catch { return null }
  },

  updateCard: async (id, data) => {
    try {
      const card = await apiUpdateCard(id, data)
      set((s) => ({ cards: s.cards.map((c) => c.id === id ? card : c) }))
      return card
    } catch { return null }
  },

  deleteCard: async (id) => {
    try {
      await apiDeleteCard(id)
      set((s) => ({ cards: s.cards.filter((c) => c.id !== id) }))
      return true
    } catch { return false }
  },

  startStudySession: async (deckId) => {
    set({ loading: true })
    try {
      const session = await apiGetAdaptiveSession(deckId)
      if (session.cards.length === 0) {
        return false
      }
      set({
        reviewSession: {
          cards: session.cards,
          currentIndex: 0,
          config: session.session_config,
          results: [],
          emotionalContext: session.emotional_context,
        },
        view: 'study',
      })
      return true
    } catch { return false } finally {
      set({ loading: false })
    }
  },

  submitReview: async (cardId, quality) => {
    try {
      const result = await apiSubmitReview(cardId, quality)
      set((s) => {
        if (!s.reviewSession) return s
        return {
          reviewSession: {
            ...s.reviewSession,
            results: [...s.reviewSession.results, result],
          },
        }
      })
      return result
    } catch { return null }
  },

  nextCard: () => {
    set((s) => {
      if (!s.reviewSession) return s
      return {
        reviewSession: {
          ...s.reviewSession,
          currentIndex: s.reviewSession.currentIndex + 1,
        },
      }
    })
  },

  endSession: () => {
    set({ reviewSession: null, view: 'decks' })
    get().fetchDecks()
    get().fetchStats()
  },

  generateFromNote: async (noteId, deckId, maxCards) => {
    set({ generating: true })
    try {
      const cards = await apiGenerateFromNote(noteId, deckId, maxCards)
      set((s) => ({ cards: [...cards, ...s.cards] }))
      return cards
    } catch { return [] } finally {
      set({ generating: false })
    }
  },

  fetchStats: async () => {
    try {
      const stats = await apiGetStats()
      set({ stats })
    } catch { /* ignore */ }
  },

  setActiveDeck: (id) => set({ activeDeckId: id }),
  setView: (view) => set({ view }),
}))
