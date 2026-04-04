"""ReAct tools for audio overview operations.

Wraps AudioService as @tool functions with user_id captured in closures.
Enables the agent to generate audio overviews from notes/flashcards
through natural conversation.
"""

from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from langchain_core.tools import tool

from infrastructure.database.session import get_session_factory
from repositories.audio_overview_repository import AudioOverviewRepository
from services.audio_service import AudioService
from schemas.audio_overview import AudioGenerateRequest
from utils.log import log_info


def build_audio_tools(user_id: str) -> list:
    """Build audio overview tools with user_id baked into closures."""

    SessionFactory = get_session_factory()

    def _svc(db_session) -> AudioService:
        return AudioService(AudioOverviewRepository(db_session))

    @tool
    def list_audio_overviews() -> str:
        """List all audio overviews for the user.

        Returns:
            JSON array of audio overviews with id, title, status,
            duration_seconds, format, source_type.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            overviews = svc.list_overviews(UUID(user_id))
            return json.dumps(
                [o.model_dump(mode="json") for o in overviews], default=str,
            )

    @tool
    def generate_audio_overview(
        source_ids: str,
        source_type: str = "notes",
        format: str = "summary",
        title: str = "",
    ) -> str:
        """Generate an audio overview (podcast/lecture/summary) from study materials.

        This creates a spoken audio version of notes, documents, or flashcards.
        The generation happens asynchronously — the audio will be ready in a few minutes.

        Args:
            source_ids: Comma-separated UUIDs of the source materials
                (note IDs, document IDs, or flashcard IDs).
            source_type: Type of source: "notes", "documents", or "flashcards".
            format: Audio format:
                - "summary": Clear spoken summary, like explaining to a friend
                - "dialogue": Teacher-student conversation discussing the content
                - "lecture": Structured academic lecture with overview and recap
            title: Optional title for the audio overview.

        Returns:
            JSON with the created audio overview (status will be "pending").
        """
        ids = [s.strip() for s in source_ids.split(",") if s.strip()]
        if not ids:
            return json.dumps({"error": "No source IDs provided"})

        with SessionFactory() as db:
            svc = _svc(db)
            overview = svc.create_overview(
                UUID(user_id),
                AudioGenerateRequest(
                    source_ids=ids,
                    source_type=source_type,
                    format=format,
                    title=title or None,
                ),
            )
            db.commit()
            return json.dumps({
                "success": True,
                "overview_id": str(overview.id),
                "title": overview.title,
                "status": overview.status,
                "message": "Audio generation started. It will be ready in a few minutes. "
                           "The user can check the Audio page to listen when it's done.",
            }, default=str)

    @tool
    def get_audio_status(overview_id: str) -> str:
        """Check the status of an audio overview generation.

        Args:
            overview_id: UUID of the audio overview.

        Returns:
            JSON with current status (pending/generating/ready/failed),
            duration, and error message if failed.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            overview = svc.get_overview(UUID(user_id), UUID(overview_id))
            if not overview:
                return json.dumps({"error": f"Audio overview {overview_id} not found"})
            return json.dumps({
                "id": str(overview.id),
                "title": overview.title,
                "status": overview.status,
                "duration_seconds": overview.duration_seconds,
                "error_message": overview.error_message,
            }, default=str)

    @tool
    def delete_audio_overview(overview_id: str) -> str:
        """Delete an audio overview.

        Args:
            overview_id: UUID of the audio overview to delete.

        Returns:
            JSON with success status.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            success = svc.delete_overview(UUID(user_id), UUID(overview_id))
            if success:
                db.commit()
            return json.dumps({"success": success, "overview_id": overview_id})

    return [
        list_audio_overviews,
        generate_audio_overview,
        get_audio_status,
        delete_audio_overview,
    ]
