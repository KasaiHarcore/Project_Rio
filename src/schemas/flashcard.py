"""Pydantic Schemas for Flashcard and FlashcardDeck models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ── Deck Schemas ──

class DeckCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)


class DeckUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)


class DeckInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = ""
    flashcard_count: int = 0
    due_count: int = 0
    created_at: datetime
    updated_at: datetime


# ── Flashcard Schemas ──

class FlashcardCreate(BaseModel):
    deck_id: str
    front: str = Field(..., max_length=5000)
    back: str = Field(..., max_length=10000)
    note_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str = "user"


class FlashcardUpdate(BaseModel):
    front: Optional[str] = Field(None, max_length=5000)
    back: Optional[str] = Field(None, max_length=10000)
    tags: Optional[List[str]] = None
    is_suspended: Optional[bool] = None


class FlashcardInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    deck_id: UUID
    note_id: Optional[UUID] = None
    front: str
    back: str
    ease_factor: float
    interval_days: int
    repetitions: int
    next_review: datetime
    source: str
    tags: List[str] = Field(default_factory=list)
    is_suspended: bool
    total_reviews: int
    correct_count: int
    streak: int
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ── Review Schemas ──

class ReviewSubmit(BaseModel):
    """SM-2 quality rating: 0-5.

    0 = Complete blackout
    1 = Wrong, but recognized answer
    2 = Wrong, but easy to recall
    3 = Correct with serious difficulty
    4 = Correct with some hesitation
    5 = Perfect response
    """
    card_id: str
    quality: int = Field(..., ge=0, le=5)


class ReviewResult(BaseModel):
    card_id: UUID
    new_interval_days: int
    new_ease_factor: float
    next_review: datetime
    is_correct: bool
    streak: int


# ── Generation Schemas ──

class GenerateFromNoteRequest(BaseModel):
    note_id: str
    deck_id: str
    max_cards: int = Field(10, ge=1, le=50)


# ── Stats ──

class FlashcardStats(BaseModel):
    total_cards: int
    due_today: int
    reviewed_today: int
    accuracy_rate: float
    longest_streak: int
    decks: List[DeckInDB] = Field(default_factory=list)
