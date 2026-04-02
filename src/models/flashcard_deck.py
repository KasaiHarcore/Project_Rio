"""FlashcardDeck model for grouping flashcards into study sets."""

import uuid
from typing import List

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base, TimestampMixin


class FlashcardDeck(Base, TimestampMixin):
    """A named collection of flashcards for study sessions.

    Attributes:
        id:          UUID primary key
        user_id:     FK -> user who owns this deck
        name:        Deck display name
        description: Optional description of the deck's contents
        flashcards:  Relationship to Flashcard (cascade delete)
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        default="",
        server_default="",
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    flashcards: Mapped[List["Flashcard"]] = relationship(
        "Flashcard",
        back_populates="deck",
        cascade="all, delete-orphan",
    )
