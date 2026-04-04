"""Repository for Flashcard and FlashcardDeck data access."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.flashcard import Flashcard
from models.flashcard_deck import FlashcardDeck
from repositories.base import BaseRepository


class FlashcardRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # ── Deck Operations ──

    def list_decks(self, user_id: UUID) -> List[FlashcardDeck]:
        return (
            self.db.query(FlashcardDeck)
            .filter(FlashcardDeck.user_id == user_id)
            .order_by(FlashcardDeck.created_at.desc())
            .all()
        )

    def get_deck(self, deck_id: UUID, user_id: UUID) -> Optional[FlashcardDeck]:
        return (
            self.db.query(FlashcardDeck)
            .filter(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id)
            .first()
        )

    def create_deck(self, deck: FlashcardDeck) -> FlashcardDeck:
        return self.add(deck)

    def delete_deck(self, deck_id: UUID, user_id: UUID) -> bool:
        deck = self.get_deck(deck_id, user_id)
        if deck:
            self.delete(deck)
            return True
        return False

    # ── Flashcard Operations ──

    def list_cards(
        self,
        user_id: UUID,
        deck_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Flashcard]:
        q = self.db.query(Flashcard).filter(Flashcard.user_id == user_id)
        if deck_id:
            q = q.filter(Flashcard.deck_id == deck_id)
        return q.order_by(Flashcard.created_at.desc()).offset(offset).limit(limit).all()

    def get_card(self, card_id: UUID, user_id: UUID) -> Optional[Flashcard]:
        return (
            self.db.query(Flashcard)
            .filter(Flashcard.id == card_id, Flashcard.user_id == user_id)
            .first()
        )

    def create_card(self, card: Flashcard) -> Flashcard:
        return self.add(card)

    def create_cards_bulk(self, cards: List[Flashcard]) -> List[Flashcard]:
        return self.add_all(cards)

    def delete_card(self, card_id: UUID, user_id: UUID) -> bool:
        card = self.get_card(card_id, user_id)
        if card:
            self.delete(card)
            return True
        return False

    # ── Review Queries ──

    def get_due_cards(
        self,
        user_id: UUID,
        deck_id: Optional[UUID] = None,
        limit: int = 20,
    ) -> List[Flashcard]:
        now = datetime.now(timezone.utc)
        q = (
            self.db.query(Flashcard)
            .filter(
                Flashcard.user_id == user_id,
                Flashcard.is_suspended == False,  # noqa: E712
                Flashcard.next_review <= now,
            )
        )
        if deck_id:
            q = q.filter(Flashcard.deck_id == deck_id)
        return q.order_by(Flashcard.next_review.asc()).limit(limit).all()

    def count_due(self, user_id: UUID, deck_id: Optional[UUID] = None) -> int:
        now = datetime.now(timezone.utc)
        q = self.db.query(func.count(Flashcard.id)).filter(
            Flashcard.user_id == user_id,
            Flashcard.is_suspended == False,  # noqa: E712
            Flashcard.next_review <= now,
        )
        if deck_id:
            q = q.filter(Flashcard.deck_id == deck_id)
        return q.scalar() or 0

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Flashcard.id))
            .filter(Flashcard.user_id == user_id)
            .scalar() or 0
        )

    def count_by_deck(self, deck_id: UUID) -> int:
        return (
            self.db.query(func.count(Flashcard.id))
            .filter(Flashcard.deck_id == deck_id)
            .scalar() or 0
        )

    def count_reviewed_today(self, user_id: UUID) -> int:
        """Count cards reviewed today using last_reviewed_at (SQL-level, no Python iteration)."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(Flashcard.id))
            .filter(
                Flashcard.user_id == user_id,
                Flashcard.last_reviewed_at >= today_start,
            )
            .scalar() or 0
        )

    def get_accuracy_stats(self, user_id: UUID):
        """Return (total_reviews_sum, correct_count_sum, max_streak) in one query."""
        row = (
            self.db.query(
                func.sum(Flashcard.total_reviews),
                func.sum(Flashcard.correct_count),
                func.max(Flashcard.streak),
            )
            .filter(Flashcard.user_id == user_id)
            .first()
        )
        return (int(row[0] or 0), int(row[1] or 0), int(row[2] or 0))

    def update_card(self, card: Flashcard) -> Flashcard:
        """Flush pending changes to a card (already mutated by caller)."""
        self.flush()
        return card
