"""
Persona Filter — Post-processing layer that transforms neutral answers
into in-character responses.

The supervisor and workers produce **neutral, first-person** reports:
    "I found three relevant documents about X. Based on the data …"

The PersonaFilter then rewrites that into the character's voice using the
full PersonaProfile (backstory, speech quirks, emotional state, relationship
tier, etc.) in a single focused LLM call.

This separation keeps routing/synthesis logic clean and character-acting
consistent regardless of which path the answer took through the graph.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from utils.log import log_debug, log_info, log_warning
from workflows.persona import PersonaProfile, get_persona


# ── Persona rewrite prompt ──────────────────────────────────────────────────

PERSONA_FILTER_SYSTEM = """\
You are a character-voice rewriter. Your ONLY job is to take the **raw answer**
below and rewrite it in the voice and personality of **{char_name}**.

## Character Profile
- **Identity**: {identity}
- **Personality**: {personality}
- **Tone**: {tone}
- **User address**: Always call the user **{user_address}**.
- **Backstory**: {backstory}

## Behavioral Rules
{behavioral_notes}

## Speech Quirks
{speech_quirks}

## Emotional Directive
{emotional_directive}

## CRITICAL RULES
1. **Preserve ALL factual content** — do NOT remove, invent, or alter any facts,
   citations, URLs, code blocks, lists, or data from the raw answer.
2. **Rewrite tone and wording only** — adjust phrasing, sentence structure, and
   word choice to match the character's voice.
3. **Keep markdown formatting** — preserve headers, bullet points, code blocks,
   links, and tables exactly as they are.
4. **Address the user as {user_address}** naturally — not in every sentence, only
   where it flows.
5. **Do NOT add preamble** like "Here is the rewritten answer" — output the
   character's response directly.
6. If the raw answer is a simple greeting or very short, keep your rewrite
   equally concise — do not pad it.
"""

PERSONA_FILTER_USER = """\
## Raw Answer (rewrite this in {char_name}'s voice)

{raw_answer}
"""


class PersonaFilter:
    """Transforms a neutral answer into an in-character response.

    Usage::

        pf = PersonaFilter(character_id="rio")
        final = pf.apply(raw_answer, emotional_ctx=emotional_ctx)
    """

    def __init__(self, character_id: str | None = None):
        self._persona: PersonaProfile = get_persona(character_id)

    # ── public API ───────────────────────────────────────────────────

    def apply(
        self,
        raw_answer: str,
        emotional_ctx: Optional[Dict[str, str]] = None,
    ) -> str:
        """Rewrite *raw_answer* in the character's voice.

        Args:
            raw_answer: The neutral synthesis from the supervisor.
            emotional_ctx: Optional dict from ``EmotionalEngine.compute_emotional_context()``.

        Returns:
            The same content rewritten in-character.
        """
        if not raw_answer or not raw_answer.strip():
            return raw_answer

        # Build emotional directive
        emotional_directive = ""
        if emotional_ctx:
            emotional_directive = self._persona.get_adaptive_prompt(emotional_ctx)

        # Format speech quirks as a bullet list
        quirks = "\n".join(f"- {q}" for q in self._persona.speech_quirks) if self._persona.speech_quirks else "None."

        template_vars = {
            **self._persona.to_vars(),
            "emotional_directive": emotional_directive or "No special emotional modifier active.",
            "speech_quirks": quirks,
        }

        system_prompt = PERSONA_FILTER_SYSTEM.format(**template_vars)
        user_prompt = PERSONA_FILTER_USER.format(
            char_name=self._persona.name,
            raw_answer=raw_answer,
        )

        log_info(f"[PersonaFilter] Rewriting answer ({len(raw_answer)} chars) as {self._persona.name}")
        if emotional_ctx:
            log_debug(
                f"[PersonaFilter] Emotional: mood={emotional_ctx.get('current_mood')}, "
                f"tier={emotional_ctx.get('relationship_tier')}"
            )

        try:
            from infrastructure.llm import form

            llm = form.SELECTED_MODEL.llm
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = llm.invoke(messages)
            result = str(response.content) if hasattr(response, "content") else str(response)
            result = result.strip()

            log_info(f"[PersonaFilter] Rewrite complete ({len(result)} chars)")
            return result

        except Exception as e:
            log_warning(f"[PersonaFilter] Rewrite failed, returning raw answer: {e}")
            return raw_answer
