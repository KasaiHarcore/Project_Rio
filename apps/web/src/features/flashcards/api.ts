import { apiFetch } from '@/shared/api/client'

/* ── Types ── */

export interface Deck {
  id: string
  user_id: string
  name: string
  description: string
  flashcard_count: number
  due_count: number
  created_at: string
  updated_at: string
}

export interface Flashcard {
  id: string
  user_id: string
  deck_id: string
  note_id: string | null
  front: string
  back: string
  ease_factor: number
  interval_days: number
  repetitions: number
  next_review: string
  source: 'agent' | 'user'
  tags: string[]
  is_suspended: boolean
  total_reviews: number
  correct_count: number
  streak: number
  created_at: string
  updated_at: string
}

export interface ReviewResult {
  card_id: string
  new_interval_days: number
  new_ease_factor: number
  next_review: string
  is_correct: boolean
  streak: number
}

export interface FlashcardStats {
  total_cards: number
  due_today: number
  reviewed_today: number
  accuracy_rate: number
  longest_streak: number
  decks: Deck[]
}

export interface AdaptiveSession {
  cards: Flashcard[]
  session_config: {
    max_cards: number
    encouragement_style: string
    difficulty_bias: string
    warmth: string
  }
  emotional_context: Record<string, string>
}

/* ── Deck API ── */

export function apiListDecks(): Promise<Deck[]> {
  return apiFetch<Deck[]>('/flashcards/decks')
}

export function apiCreateDeck(name: string, description = ''): Promise<Deck> {
  return apiFetch<Deck>('/flashcards/decks', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })
}

export function apiUpdateDeck(id: string, data: { name?: string; description?: string }): Promise<Deck> {
  return apiFetch<Deck>(`/flashcards/decks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteDeck(id: string): Promise<void> {
  await apiFetch(`/flashcards/decks/${id}`, { method: 'DELETE' })
}

/* ── Card API ── */

export function apiListCards(deckId?: string, limit = 50, offset = 0): Promise<Flashcard[]> {
  const params = new URLSearchParams()
  if (deckId) params.set('deck_id', deckId)
  params.set('limit', String(limit))
  params.set('offset', String(offset))
  return apiFetch<Flashcard[]>(`/flashcards/cards?${params}`)
}

export function apiCreateCard(data: { deck_id: string; front: string; back: string; tags?: string[] }): Promise<Flashcard> {
  return apiFetch<Flashcard>('/flashcards/cards', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function apiUpdateCard(
  id: string,
  data: { front?: string; back?: string; tags?: string[]; is_suspended?: boolean },
): Promise<Flashcard> {
  return apiFetch<Flashcard>(`/flashcards/cards/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteCard(id: string): Promise<void> {
  await apiFetch(`/flashcards/cards/${id}`, { method: 'DELETE' })
}

/* ── Review API ── */

export function apiGetDueCards(deckId?: string, limit = 20): Promise<Flashcard[]> {
  const params = new URLSearchParams()
  if (deckId) params.set('deck_id', deckId)
  params.set('limit', String(limit))
  return apiFetch<Flashcard[]>(`/flashcards/due?${params}`)
}

export function apiSubmitReview(cardId: string, quality: number): Promise<ReviewResult> {
  return apiFetch<ReviewResult>('/flashcards/review', {
    method: 'POST',
    body: JSON.stringify({ card_id: cardId, quality }),
  })
}

/* ── Generation ── */

export function apiGenerateFromNote(noteId: string, deckId: string, maxCards = 10): Promise<Flashcard[]> {
  return apiFetch<Flashcard[]>('/flashcards/generate/note', {
    method: 'POST',
    body: JSON.stringify({ note_id: noteId, deck_id: deckId, max_cards: maxCards }),
  })
}

/* ── Stats & Session ── */

export function apiGetStats(): Promise<FlashcardStats> {
  return apiFetch<FlashcardStats>('/flashcards/stats')
}

export function apiGetAdaptiveSession(deckId?: string, maxCards = 20): Promise<AdaptiveSession> {
  const params = new URLSearchParams()
  if (deckId) params.set('deck_id', deckId)
  params.set('max_cards', String(maxCards))
  return apiFetch<AdaptiveSession>(`/flashcards/session?${params}`)
}
