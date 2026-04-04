"""Flashcard CRUD and spaced repetition review endpoints.

Provides:
    GET    /flashcards/decks                 – list decks
    POST   /flashcards/decks                 – create deck
    PATCH  /flashcards/decks/{id}            – update deck
    DELETE /flashcards/decks/{id}            – delete deck
    GET    /flashcards/cards                 – list cards
    POST   /flashcards/cards                 – create card
    DELETE /flashcards/cards/{id}            – delete card
    GET    /flashcards/due                   – get due cards for review
    POST   /flashcards/review               – submit review result
    POST   /flashcards/generate/note         – generate cards from a note
    GET    /flashcards/stats                 – study statistics
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_flashcard_service
from core.exceptions import NotFoundError
from models.user import User
from schemas.flashcard import (
    DeckCreate,
    DeckUpdate,
    DeckInDB,
    FlashcardCreate,
    FlashcardUpdate,
    FlashcardInDB,
    ReviewSubmit,
    ReviewResult,
    GenerateFromNoteRequest,
    FlashcardStats,
)
from services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


# ── Decks ──

@router.get("/decks", response_model=List[DeckInDB])
async def list_decks(
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """List all flashcard decks for the authenticated user."""
    return await concurrency_manager.run_in_thread(svc.list_decks, user.id)


@router.post("/decks", response_model=DeckInDB, status_code=status.HTTP_201_CREATED)
async def create_deck(
    body: DeckCreate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Create a new flashcard deck."""
    return await concurrency_manager.run_in_thread(svc.create_deck, user.id, body)


@router.patch("/decks/{deck_id}", response_model=DeckInDB)
async def update_deck(
    deck_id: UUID,
    body: DeckUpdate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Update a flashcard deck."""
    result = await concurrency_manager.run_in_thread(svc.update_deck, user.id, deck_id, body)
    if not result:
        raise NotFoundError("Deck not found")
    return result


@router.delete("/decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Delete a flashcard deck and all its cards."""
    ok = await concurrency_manager.run_in_thread(svc.delete_deck, user.id, deck_id)
    if not ok:
        raise NotFoundError("Deck not found")


# ── Flashcards ──

@router.get("/cards", response_model=List[FlashcardInDB])
async def list_cards(
    deck_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """List flashcards, optionally filtered by deck."""
    return await concurrency_manager.run_in_thread(
        svc.list_cards, user.id, deck_id, limit, offset,
    )


@router.post("/cards", response_model=FlashcardInDB, status_code=status.HTTP_201_CREATED)
async def create_card(
    body: FlashcardCreate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Create a single flashcard."""
    return await concurrency_manager.run_in_thread(svc.create_card, user.id, body)


@router.patch("/cards/{card_id}", response_model=FlashcardInDB)
async def update_card(
    card_id: UUID,
    body: FlashcardUpdate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Update flashcard content or suspension status."""
    result = await concurrency_manager.run_in_thread(svc.update_card, user.id, card_id, body)
    if not result:
        raise NotFoundError("Card not found")
    return result


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: UUID,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Delete a flashcard."""
    ok = await concurrency_manager.run_in_thread(svc.delete_card, user.id, card_id)
    if not ok:
        raise NotFoundError("Card not found")


# ── Adaptive Session ──

@router.get("/session")
async def get_adaptive_session(
    deck_id: Optional[UUID] = Query(None),
    max_cards: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Get an adaptive study session adjusted by emotional state.

    Returns cards, session config (encouragement style, difficulty bias),
    and the current emotional context.
    """
    return await concurrency_manager.run_in_thread(
        svc.adaptive_session, user.id, deck_id, max_cards,
    )


# ── Review ──

@router.get("/due", response_model=List[FlashcardInDB])
async def get_due_cards(
    deck_id: Optional[UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Get flashcards due for review."""
    return await concurrency_manager.run_in_thread(
        svc.get_due_cards, user.id, deck_id, limit,
    )


@router.post("/review", response_model=ReviewResult)
async def submit_review(
    body: ReviewSubmit,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Submit a review result using SM-2 quality rating (0-5)."""
    result = await concurrency_manager.run_in_thread(svc.submit_review, user.id, body)
    if not result:
        raise NotFoundError("Card not found")
    return result


# ── Generation ──

@router.post("/generate/note", response_model=List[FlashcardInDB])
async def generate_from_note(
    body: GenerateFromNoteRequest,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Generate flashcards from a note using AI."""
    return await concurrency_manager.run_in_thread(
        svc.generate_from_note, user.id,
        UUID(body.note_id), UUID(body.deck_id), body.max_cards,
    )


# ── Stats ──

@router.get("/stats", response_model=FlashcardStats)
async def get_stats(
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(get_flashcard_service),
):
    """Get flashcard study statistics."""
    return await concurrency_manager.run_in_thread(svc.get_stats, user.id)
