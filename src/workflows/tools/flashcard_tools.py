"""ReAct tools for flashcard operations.

Wraps FlashcardService as @tool functions with user_id captured in closures.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from infrastructure.database.session import get_session_factory
from repositories.flashcard_repository import FlashcardRepository
from services.flashcard_service import FlashcardService
from schemas.flashcard import DeckCreate, FlashcardCreate
from utils.log import log_info


def build_flashcard_tools(user_id: str) -> list:
    """Build flashcard tools with user_id baked into closures."""

    SessionFactory = get_session_factory()

    def _svc(db_session) -> FlashcardService:
        return FlashcardService(FlashcardRepository(db_session))

    @tool
    def list_flashcard_decks() -> str:
        """List all flashcard decks with card counts and due counts.

        Returns:
            JSON array of decks with id, name, flashcard_count, due_count.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            decks = svc.list_decks(UUID(user_id))
            return json.dumps(
                [d.model_dump(mode="json") for d in decks], default=str,
            )

    @tool
    def create_flashcard_deck(name: str, description: str = "") -> str:
        """Create a new flashcard deck.

        Args:
            name: Deck display name.
            description: Optional description.

        Returns:
            JSON with the created deck object.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            deck = svc.create_deck(UUID(user_id), DeckCreate(name=name, description=description))
            db.commit()
            return json.dumps(deck.model_dump(mode="json"), default=str)

    @tool
    def get_due_flashcards(deck_id: Optional[str] = None, limit: int = 20) -> str:
        """Get flashcards due for review today.

        Args:
            deck_id: Optional deck UUID to filter by.
            limit: Maximum number of cards to return.

        Returns:
            JSON array of due flashcards with front, back, and scheduling info.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            cards = svc.get_due_cards(
                UUID(user_id),
                UUID(deck_id) if deck_id else None,
                limit,
            )
            return json.dumps(
                [c.model_dump(mode="json") for c in cards], default=str,
            )

    @tool
    def create_flashcard(deck_id: str, front: str, back: str, tags: str = "") -> str:
        """Create a single flashcard manually.

        Args:
            deck_id: UUID of the target deck.
            front: Question/prompt text.
            back: Answer text.
            tags: Comma-separated tags (optional).

        Returns:
            JSON with the created flashcard object.
        """
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        with SessionFactory() as db:
            svc = _svc(db)
            card = svc.create_card(
                UUID(user_id),
                FlashcardCreate(deck_id=deck_id, front=front, back=back, tags=tag_list),
            )
            db.commit()
            return json.dumps(card.model_dump(mode="json"), default=str)

    @tool
    def generate_flashcards_from_note(
        note_id: str,
        deck_id: str,
        max_cards: int = 10,
    ) -> str:
        """Generate flashcards from a note using AI.

        Args:
            note_id: UUID of the source note.
            deck_id: UUID of the target deck.
            max_cards: Maximum number of cards to generate (default 10).

        Returns:
            JSON with generated count and card objects.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            cards = svc.generate_from_note(
                UUID(user_id), UUID(note_id), UUID(deck_id), max_cards,
            )
            db.commit()
            return json.dumps({
                "generated": len(cards),
                "cards": [c.model_dump(mode="json") for c in cards],
            }, default=str)

    @tool
    def get_flashcard_stats() -> str:
        """Get flashcard study statistics.

        Returns:
            JSON with total_cards, due_today, reviewed_today, accuracy_rate,
            longest_streak, and deck summaries.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            stats = svc.get_stats(UUID(user_id))
            return json.dumps(stats.model_dump(mode="json"), default=str)

    return [
        list_flashcard_decks,
        create_flashcard_deck,
        get_due_flashcards,
        create_flashcard,
        generate_flashcards_from_note,
        get_flashcard_stats,
    ]
