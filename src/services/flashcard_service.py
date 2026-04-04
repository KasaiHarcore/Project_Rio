"""Flashcard service with SM-2 spaced repetition algorithm."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from models.flashcard import Flashcard, FlashcardSource
from models.flashcard_deck import FlashcardDeck
from repositories.flashcard_repository import FlashcardRepository
from schemas.flashcard import (
    DeckCreate,
    DeckInDB,
    FlashcardCreate,
    FlashcardInDB,
    ReviewSubmit,
    ReviewResult,
    FlashcardStats,
)
from utils.log import log_info, log_warning


class FlashcardService:
    def __init__(self, repo: FlashcardRepository) -> None:
        self._repo = repo

    # ── SM-2 Algorithm ──────────────────���───────────────────────────

    @staticmethod
    def sm2_update(
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval_days: int,
    ) -> Tuple[int, float, int]:
        """SM-2 spaced repetition algorithm.

        Args:
            quality: User rating 0-5 (0=blackout, 5=perfect)
            repetitions: Current repetition count
            ease_factor: Current ease factor (>= 1.3)
            interval_days: Current interval in days

        Returns:
            (new_repetitions, new_ease_factor, new_interval_days)
        """
        if quality < 3:
            # Failed — reset to beginning
            return 0, max(1.3, ease_factor - 0.2), 1

        # Successful review
        new_repetitions = repetitions + 1

        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)

        # Update ease factor
        new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease = max(1.3, new_ease)

        return new_repetitions, new_ease, max(1, new_interval)

    # ── Deck CRUD ───────────────────────────────────────────────────

    def list_decks(self, user_id: UUID) -> List[DeckInDB]:
        decks = self._repo.list_decks(user_id)
        result = []
        for d in decks:
            card_count = self._repo.count_by_deck(d.id)
            due_count = self._repo.count_due(user_id, d.id)
            result.append(DeckInDB(
                id=d.id,
                user_id=d.user_id,
                name=d.name,
                description=d.description or "",
                flashcard_count=card_count,
                due_count=due_count,
                created_at=d.created_at,
                updated_at=d.updated_at,
            ))
        return result

    def create_deck(self, user_id: UUID, data: DeckCreate) -> DeckInDB:
        deck = FlashcardDeck(
            id=uuid4(),
            user_id=user_id,
            name=data.name,
            description=data.description,
        )
        deck = self._repo.create_deck(deck)
        return DeckInDB(
            id=deck.id,
            user_id=deck.user_id,
            name=deck.name,
            description=deck.description or "",
            flashcard_count=0,
            due_count=0,
            created_at=deck.created_at,
            updated_at=deck.updated_at,
        )

    def update_deck(self, user_id: UUID, deck_id: UUID, data) -> Optional[DeckInDB]:
        deck = self._repo.get_deck(deck_id, user_id)
        if not deck:
            return None
        if data.name is not None:
            deck.name = data.name
        if data.description is not None:
            deck.description = data.description
        self._repo.flush()
        card_count = self._repo.count_by_deck(deck.id)
        due_count = self._repo.count_due(user_id, deck.id)
        return DeckInDB(
            id=deck.id,
            user_id=deck.user_id,
            name=deck.name,
            description=deck.description or "",
            flashcard_count=card_count,
            due_count=due_count,
            created_at=deck.created_at,
            updated_at=deck.updated_at,
        )

    def delete_deck(self, user_id: UUID, deck_id: UUID) -> bool:
        return self._repo.delete_deck(deck_id, user_id)

    # ── Flashcard CRUD ─────────────────────────────��────────────────

    def list_cards(
        self,
        user_id: UUID,
        deck_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FlashcardInDB]:
        cards = self._repo.list_cards(user_id, deck_id, limit, offset)
        return [FlashcardInDB.model_validate(c) for c in cards]

    def create_card(self, user_id: UUID, data: FlashcardCreate) -> FlashcardInDB:
        card = Flashcard(
            id=uuid4(),
            user_id=user_id,
            deck_id=UUID(data.deck_id),
            note_id=UUID(data.note_id) if data.note_id else None,
            front=data.front,
            back=data.back,
            tags=data.tags,
            source=FlashcardSource(data.source),
        )
        card = self._repo.create_card(card)
        return FlashcardInDB.model_validate(card)

    def create_cards_bulk(
        self,
        user_id: UUID,
        cards_data: List[FlashcardCreate],
    ) -> List[FlashcardInDB]:
        cards = []
        for data in cards_data:
            cards.append(Flashcard(
                id=uuid4(),
                user_id=user_id,
                deck_id=UUID(data.deck_id),
                note_id=UUID(data.note_id) if data.note_id else None,
                front=data.front,
                back=data.back,
                tags=data.tags,
                source=FlashcardSource(data.source),
            ))
        created = self._repo.create_cards_bulk(cards)
        return [FlashcardInDB.model_validate(c) for c in created]

    def delete_card(self, user_id: UUID, card_id: UUID) -> bool:
        return self._repo.delete_card(card_id, user_id)

    # ── Review ──────────────────────────────────────────────────────

    def get_due_cards(
        self,
        user_id: UUID,
        deck_id: Optional[UUID] = None,
        limit: int = 20,
    ) -> List[FlashcardInDB]:
        cards = self._repo.get_due_cards(user_id, deck_id, limit)
        return [FlashcardInDB.model_validate(c) for c in cards]

    def submit_review(self, user_id: UUID, review: ReviewSubmit) -> Optional[ReviewResult]:
        card = self._repo.get_card(UUID(review.card_id), user_id)
        if not card:
            return None

        new_reps, new_ease, new_interval = self.sm2_update(
            quality=review.quality,
            repetitions=card.repetitions,
            ease_factor=card.ease_factor,
            interval_days=card.interval_days,
        )

        now = datetime.now(timezone.utc)
        is_correct = review.quality >= 3

        card.repetitions = new_reps
        card.ease_factor = new_ease
        card.interval_days = new_interval
        card.next_review = now + timedelta(days=new_interval)
        card.total_reviews += 1
        card.last_reviewed_at = now
        if is_correct:
            card.correct_count += 1
            card.streak += 1
        else:
            card.streak = 0

        self._repo.flush()

        return ReviewResult(
            card_id=card.id,
            new_interval_days=new_interval,
            new_ease_factor=round(new_ease, 2),
            next_review=card.next_review,
            is_correct=is_correct,
            streak=card.streak,
        )

    # ── Adaptive Session (emotional engine integration) ───────────

    def adaptive_session(
        self,
        user_id: UUID,
        deck_id: Optional[UUID] = None,
        max_cards: int = 20,
    ) -> dict:
        """Create an adaptive study session based on emotional state.

        Uses the emotional engine to adjust session parameters:
        - Tired/sad mood → fewer cards, easier bias, gentle encouragement
        - Frustrated → review-only mode, supportive tone
        - Excited/happy + high energy → full cards, challenging bias
        - Default → balanced session

        Returns:
            {
                "cards": [...],
                "session_config": {
                    "max_cards": int,
                    "encouragement_style": str,
                    "difficulty_bias": str,
                },
                "emotional_context": {...},
            }
        """
        # Get emotional context
        emotional_context = {}
        try:
            from infrastructure.database.session import get_session_factory
            from services.emotional_engine import EmotionalEngine
            from repositories.emotional_state_repository import EmotionalStateRepository

            SessionFactory = get_session_factory()
            with SessionFactory() as db:
                engine = EmotionalEngine(EmotionalStateRepository(db))
                emotional_context = engine.compute_emotional_context(user_id, "rio")
        except Exception as e:
            log_warning(f"[Flashcard] Failed to get emotional context: {e}")

        mood = emotional_context.get("current_mood", "neutral")
        energy_str = emotional_context.get("energy_level", "50%")
        try:
            energy = float(energy_str.rstrip("%")) / 100
        except (ValueError, AttributeError):
            energy = 0.5
        tier = emotional_context.get("relationship_tier", "acquaintance")

        # Adapt session parameters based on emotional state
        if mood in ("tired", "sad") or energy < 0.3:
            adjusted_max = min(max_cards, 8)
            difficulty_bias = "easy"
            encouragement = "gentle"
        elif mood == "frustrated":
            adjusted_max = min(max_cards, 5)
            difficulty_bias = "review_only"
            encouragement = "supportive"
        elif mood in ("excited", "happy") and energy > 0.7:
            adjusted_max = max_cards
            difficulty_bias = "challenging"
            encouragement = "brief"
        else:
            adjusted_max = max_cards
            difficulty_bias = "balanced"
            encouragement = "standard"

        # Adjust encouragement warmth by relationship tier
        tier_warmth = {
            "stranger": "formal",
            "acquaintance": "friendly",
            "friend": "warm",
            "close_friend": "playful",
            "bonded": "loving",
        }
        warmth = tier_warmth.get(tier, "friendly")

        # Get due cards
        cards = self.get_due_cards(user_id, deck_id, adjusted_max)

        # Sort by difficulty bias
        if difficulty_bias == "easy":
            cards.sort(key=lambda c: c.ease_factor, reverse=True)
        elif difficulty_bias == "challenging":
            cards.sort(key=lambda c: c.ease_factor)

        return {
            "cards": [c.model_dump(mode="json") for c in cards],
            "session_config": {
                "max_cards": adjusted_max,
                "encouragement_style": encouragement,
                "difficulty_bias": difficulty_bias,
                "warmth": warmth,
            },
            "emotional_context": emotional_context,
        }

    # ── AI Generation ───────────────────────────────────────────────

    def generate_from_note(
        self,
        user_id: UUID,
        note_id: UUID,
        deck_id: UUID,
        max_cards: int = 10,
    ) -> List[FlashcardInDB]:
        """Use LLM to generate flashcards from note content."""
        import json

        from infrastructure.database.session import get_session_factory

        SessionFactory = get_session_factory()
        with SessionFactory() as db:
            from models.note import Note
            note = db.query(Note).filter(
                Note.id == note_id, Note.user_id == user_id,
            ).first()
            if not note:
                log_warning(f"Note {note_id} not found for flashcard generation")
                return []
            note_content = f"# {note.title}\n\n{note.content}"

        from infrastructure.llm import form
        if not form.SELECTED_MODEL or not getattr(form.SELECTED_MODEL, "llm", None):
            if form.SELECTED_MODEL:
                form.SELECTED_MODEL.setup()

        prompt = (
            f"Extract up to {max_cards} key concepts from this note and create flashcards.\n"
            "Return ONLY a JSON array of objects with \"front\" (question) and \"back\" (answer) keys.\n"
            "Keep questions specific and answers concise but complete.\n\n"
            f"Note content:\n{note_content[:8000]}\n\nJSON array:"
        )

        try:
            response = form.SELECTED_MODEL.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Robustly extract the first JSON array from anywhere in the response
            start = content.find("[")
            end = content.rfind("]")
            if start == -1 or end == -1 or end <= start:
                log_warning(f"No JSON array found in flashcard generation response")
                return []
            content = content[start:end + 1]

            pairs = json.loads(content)
        except json.JSONDecodeError as e:
            log_warning(f"Failed to parse flashcard generation JSON: {e}")
            return []
        except Exception as e:
            log_warning(f"Flashcard generation failed: {e}")
            return []

        if not isinstance(pairs, list):
            return []

        cards_data = [
            FlashcardCreate(
                deck_id=str(deck_id),
                front=p["front"],
                back=p["back"],
                note_id=str(note_id),
                source="agent",
            )
            for p in pairs
            if isinstance(p, dict) and "front" in p and "back" in p
        ][:max_cards]

        if not cards_data:
            return []

        return self.create_cards_bulk(user_id, cards_data)

    # ── Card Update ─────────────────────────────────────────────────

    def update_card(self, user_id: UUID, card_id: UUID, data) -> Optional[FlashcardInDB]:
        card = self._repo.get_card(card_id, user_id)
        if not card:
            return None
        if data.front is not None:
            card.front = data.front
        if data.back is not None:
            card.back = data.back
        if data.tags is not None:
            card.tags = data.tags
        if data.is_suspended is not None:
            card.is_suspended = data.is_suspended
        self._repo.flush()
        return FlashcardInDB.model_validate(card)

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self, user_id: UUID) -> FlashcardStats:
        from repositories.flashcard_repository import FlashcardRepository

        due = self._repo.count_due(user_id)
        total_cards = self._repo.count_by_user(user_id)
        reviewed_today = self._repo.count_reviewed_today(user_id)
        total_reviews, total_correct, longest_streak = self._repo.get_accuracy_stats(user_id)
        decks = self.list_decks(user_id)

        accuracy = total_correct / total_reviews if total_reviews > 0 else 0.0

        return FlashcardStats(
            total_cards=total_cards,
            due_today=due,
            reviewed_today=reviewed_today,
            accuracy_rate=round(accuracy, 3),
            longest_streak=longest_streak,
            decks=decks,
        )
