"""Audio service for generating audio overviews from study materials.

Generates conversational scripts from source content using LLM,
then synthesizes audio using Qwen3-TTS with voice cloning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from models.audio_overview import AudioOverview, AudioFormat, AudioSourceType, AudioStatus
from repositories.audio_overview_repository import AudioOverviewRepository
from schemas.audio_overview import AudioGenerateRequest, AudioOverviewInDB
from utils.log import log_info, log_warning, log_error

AUDIO_STORAGE_DIR = Path("storage/audio")


class AudioService:
    def __init__(self, repo: AudioOverviewRepository) -> None:
        self._repo = repo

    def list_overviews(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[AudioOverviewInDB]:
        overviews = self._repo.list_by_user(user_id, limit, offset)
        return [AudioOverviewInDB.model_validate(o) for o in overviews]

    def get_overview(self, user_id: UUID, overview_id: UUID) -> Optional[AudioOverviewInDB]:
        overview = self._repo.get_by_id(overview_id, user_id)
        if not overview:
            return None
        return AudioOverviewInDB.model_validate(overview)

    def delete_overview(self, user_id: UUID, overview_id: UUID) -> bool:
        overview = self._repo.get_by_id(overview_id, user_id)
        if not overview:
            return False
        # Clean up audio file
        if overview.audio_path and os.path.exists(overview.audio_path):
            try:
                os.remove(overview.audio_path)
            except OSError:
                pass
        return self._repo.delete_by_id(overview_id, user_id)

    def create_overview(
        self,
        user_id: UUID,
        data: AudioGenerateRequest,
    ) -> AudioOverviewInDB:
        """Create an audio overview record and start generation."""
        title = data.title or f"Audio Overview ({data.source_type})"

        overview = AudioOverview(
            id=uuid4(),
            user_id=user_id,
            title=title,
            source_ids=data.source_ids,
            source_type=AudioSourceType(data.source_type),
            format=AudioFormat(data.format),
            status=AudioStatus.PENDING,
        )
        overview = self._repo.create(overview)
        result = AudioOverviewInDB.model_validate(overview)

        # Start generation in background
        from core.concurrency import concurrency_manager
        overview_id = overview.id
        concurrency_manager.submit_fire_and_forget(
            lambda: self._generate_async(user_id, overview_id, data),
        )

        return result

    def _generate_async(
        self,
        user_id: UUID,
        overview_id: UUID,
        data: AudioGenerateRequest,
    ) -> None:
        """Background generation: fetch content -> LLM script -> TTS audio."""
        from infrastructure.database.session import get_session_factory

        SessionFactory = get_session_factory()
        try:
            with SessionFactory() as db:
                repo = AudioOverviewRepository(db)
                overview = repo.get_by_id(overview_id, user_id)
                if not overview:
                    return

                overview.status = AudioStatus.GENERATING
                repo.flush()
                db.commit()

            # Step 1: Fetch source content
            content = self._fetch_source_content(user_id, data.source_ids, data.source_type)
            if not content:
                self._mark_failed(user_id, overview_id, "No source content found")
                return

            # Step 2: Generate script via LLM
            script = self._generate_script(content, data.format)
            if not script:
                self._mark_failed(user_id, overview_id, "Script generation failed")
                return

            # Step 3: Synthesize audio via TTS
            audio_path, duration = self._synthesize_audio(str(overview_id), script)
            if not audio_path:
                self._mark_failed(user_id, overview_id, "Audio synthesis failed")
                return

            # Step 4: Update record
            with SessionFactory() as db:
                repo = AudioOverviewRepository(db)
                overview = repo.get_by_id(overview_id, user_id)
                if overview:
                    overview.transcript = script
                    overview.audio_path = audio_path
                    overview.duration_seconds = duration
                    overview.status = AudioStatus.READY
                    repo.flush()
                    db.commit()

            log_info(f"[Audio] Generated overview {overview_id} ({duration}s)")

        except Exception as e:
            log_error(f"[Audio] Generation failed for {overview_id}: {e}")
            self._mark_failed(user_id, overview_id, str(e))

    def _mark_failed(self, user_id: UUID, overview_id: UUID, error: str) -> None:
        from infrastructure.database.session import get_session_factory
        SessionFactory = get_session_factory()
        try:
            with SessionFactory() as db:
                repo = AudioOverviewRepository(db)
                overview = repo.get_by_id(overview_id, user_id)
                if overview:
                    overview.status = AudioStatus.FAILED
                    overview.error_message = error[:2000]
                    repo.flush()
                    db.commit()
        except Exception:
            pass

    def _fetch_source_content(
        self,
        user_id: UUID,
        source_ids: List[str],
        source_type: str,
    ) -> str:
        """Fetch content from source notes/documents."""
        from infrastructure.database.session import get_session_factory

        SessionFactory = get_session_factory()
        parts = []

        with SessionFactory() as db:
            if source_type == "notes":
                from models.note import Note
                for sid in source_ids:
                    try:
                        note = db.query(Note).filter(
                            Note.id == UUID(sid), Note.user_id == user_id,
                        ).first()
                        if note:
                            parts.append(f"## {note.title or 'Untitled'}\n\n{note.content}")
                    except Exception:
                        continue

            elif source_type == "flashcards":
                from models.flashcard import Flashcard
                for sid in source_ids:
                    try:
                        card = db.query(Flashcard).filter(
                            Flashcard.id == UUID(sid), Flashcard.user_id == user_id,
                        ).first()
                        if card:
                            parts.append(f"Q: {card.front}\nA: {card.back}")
                    except Exception:
                        continue

        return "\n\n---\n\n".join(parts)

    def _generate_script(self, content: str, format: str) -> Optional[str]:
        """Use LLM to generate a conversational script."""
        from infrastructure.llm import form

        if not form.SELECTED_MODEL or not getattr(form.SELECTED_MODEL, "llm", None):
            if form.SELECTED_MODEL:
                form.SELECTED_MODEL.setup()

        if not form.SELECTED_MODEL or not form.SELECTED_MODEL.llm:
            log_warning("[Audio] No LLM available for script generation")
            return None

        format_instructions = {
            "summary": (
                "Create a clear, engaging spoken summary of this content. "
                "Use a natural conversational tone as if explaining to a friend. "
                "Highlight key concepts and important details."
            ),
            "dialogue": (
                "Create a dialogue between a teacher and student discussing this content. "
                "The teacher explains concepts clearly, the student asks insightful questions. "
                "Keep it natural and educational."
            ),
            "lecture": (
                "Create a structured lecture script covering this content. "
                "Start with an overview, cover each topic in depth, and end with a summary. "
                "Use a professional but engaging academic tone."
            ),
        }

        instruction = format_instructions.get(format, format_instructions["summary"])

        prompt = (
            f"{instruction}\n\n"
            "Rules:\n"
            "- Write ONLY the spoken text — no stage directions, no [pause] markers.\n"
            "- Keep it between 500-2000 words.\n"
            "- Make it suitable for text-to-speech synthesis.\n\n"
            f"Source material:\n{content[:12000]}\n\n"
            "Script:"
        )

        try:
            response = form.SELECTED_MODEL.llm.invoke(prompt)
            script = response.content if hasattr(response, "content") else str(response)
            return script.strip()
        except Exception as e:
            log_error(f"[Audio] Script generation failed: {e}")
            return None

    def _synthesize_audio(self, overview_id: str, script: str) -> tuple[Optional[str], int]:
        """Synthesize audio from script text using Qwen3-TTS voice cloning.

        Returns (file_path, duration_seconds) or (None, 0) on failure.
        """
        AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(AUDIO_STORAGE_DIR / f"{overview_id}.wav")

        try:
            from infrastructure.tts.qwen3_engine import get_qwen3_engine
            from core.settings import get_tts_config

            config = get_tts_config()
            engine = get_qwen3_engine()

            if engine is None:
                log_error("[Audio] Qwen3-TTS engine not available (check TTS_ENGINE config)")
                return None, 0

            result = engine.synthesize(script, language=config.language)
            if result is None:
                log_error("[Audio] Qwen3-TTS synthesis returned no audio")
                return None, 0

            wav_data, sample_rate = result

            import soundfile as sf
            sf.write(output_path, wav_data, sample_rate)

            duration = len(wav_data) / sample_rate
            log_info(f"[Audio] Synthesized {int(duration)}s audio with Qwen3-TTS")
            return output_path, max(1, int(duration))

        except Exception as e:
            log_error(f"[Audio] TTS synthesis failed: {e}")
            return None, 0
