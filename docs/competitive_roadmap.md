# Project Rio: Competitive Analysis & Feature Roadmap

> Generated from deep competitive research across 30+ similar products/projects.
> Last updated: 2026-04-01

---

## Table of Contents

1. [Competitive Landscape](#1-competitive-landscape)
2. [Rio's Position](#2-rios-position)
3. [Development Roadmap Overview](#3-development-roadmap-overview)
4. [Layer 1: Quick Wins on Existing Infrastructure](#4-layer-1-quick-wins-on-existing-infrastructure)
   - [1.1 Contextual Note Resurfacing](#11-contextual-note-resurfacing)
   - [1.2 Spaced Repetition / Flashcard System](#12-spaced-repetition--flashcard-system-phase-1)
   - [1.3 Scheduled Automations](#13-scheduled-automations)
5. [Layer 2: Infrastructure Extensions](#5-layer-2-infrastructure-extensions)
   - [2.1 MCP Protocol Support](#21-mcp-protocol-support-client-side)
   - [2.2 Audio Overview / Podcast Generation](#22-audio-overview--podcast-generation)
   - [2.3 Adaptive Flashcards (Phase 2)](#23-adaptive-flashcards-phase-2)
6. [Layer 3: Differentiation Features](#6-layer-3-differentiation-features)
   - [3.1 Deep Research Mode](#31-deep-research-mode)
   - [3.2 Vision-based Input](#32-vision-based-input)
   - [3.3 Calendar Integration](#33-calendar-integration)
   - [3.4 Temporal Knowledge Graph](#34-temporal-knowledge-graph)
   - [3.5 Emotional Voice](#35-emotional-voice)
7. [Layer 4: Advanced Platform](#7-layer-4-advanced-platform)
8. [Architecture Patterns to Adopt](#8-architecture-patterns-to-adopt)
9. [Protocols & Standards](#9-protocols--standards)
10. [Priority Matrix](#10-priority-matrix)

---

## 1. Competitive Landscape

### A. AI-Powered Study/Learning Assistants

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **Khanmigo** (Khan Academy) | khanmigo.ai | Socratic questioning engine, LMS integration (Canvas, Google Classroom), image-based problem input, 10+ languages, teacher tools | Socratic questioning mode, standards-aligned content grounding |
| **Google NotebookLM** | notebooklm.google.com | Audio Overview (AI podcast from your content), Deep Research mode, flashcard/quiz generation, source-grounded answers | Audio overview is category-defining, source-grounding reduces hallucination |
| **Quizlet AI** (Q-Chat) | quizlet.com/features/ai-study-tools | SM-2 spaced repetition, Magic Notes (auto flashcards from uploads), Brain Beats (study songs), 800M+ community study sets | Spaced repetition is non-negotiable for study positioning |
| **Duolingo** (Birdbrain) | duolingo.com | Birdbrain adaptive difficulty engine (updated daily from 1.25B exercises), zone of proximal development targeting, deep gamification (streaks, leagues, hearts, XP) | Adaptive difficulty adjusting to user emotional state + performance |

### B. AI-Powered Personal Productivity Agents

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **Notion AI** | notion.com/product/ai | Autonomous 20-min agents across hundreds of pages, cross-tool integration (Slack, Jira, Drive), auto-model selection (GPT-5.2/Claude/Gemini), Custom Agent builder | Cross-tool integration via MCP, auto-model routing by task complexity |
| **Taskade** | taskade.com | AI sprint planning, Gantt/Kanban boards, trigger-based automation workflows, Agile/Waterfall methodology support, real-time collaboration | Trigger-based automations (cron + event-driven) |
| **Motion AI** | usemotion.com | Named AI Employees (Alfred/Chip/Millie) with distinct roles, SOP-to-workflow automation, calendar AI with time-blocking | Named agent personas with roles, SOP-to-workflow |
| **Mem.ai** | get.mem.ai | Agentic Chat (AI creates/edits/organizes notes), Deep Search (meaning-based), "Heads Up" (auto-resurfaces relevant notes before meetings) | Contextual note resurfacing is high-impact and low-effort for Rio |
| **Reclaim.ai** | reclaim.ai | Focus Time protection, habits scheduling, smart calendar sync, priority-based auto-rescheduling | Calendar-aware mission scheduling |

### C. Open-Source AI Agent Frameworks

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **CrewAI** | github.com/joaomdmoura/crewAI | Role-playing agent "crews" with backstories/goals, sequential/parallel/hierarchical assembly, 280% adoption growth in 2025 | Agent crew patterns for complex multi-step tasks |
| **Letta** (MemGPT) | letta.com | LLM-as-OS memory (core=RAM, recall=cache, archival=disk), self-editing memory, Conversations API (shared memory across sessions), 94.8% DMR benchmark | Tiered memory architecture is the gold standard |
| **OpenHands** | openhands.dev | CodeAct architecture for code/web/commands, sandboxed execution, GitHub integration (auto code reviews, test gen), 32K stars, 188+ contributors | Sandboxed execution environments for OS control |
| **OpenClaw** | openclaw.ai | Multi-channel messaging UI (WhatsApp, Telegram, Slack, Discord, Signal), skills-as-directories pattern, 247K stars in 60 days | Skills-as-directories for modular capabilities |
| **Khoj** | khoj.dev | Self-hostable personal AI, Obsidian/Emacs plugin, WhatsApp access, scheduled automations (cron-based), fully offline capability, custom agents with personas | Most directly comparable to Rio. Scheduled automations + plugin ecosystem |
| **PyGPT** | pygpt.net | 11 operational modes, image/video generation, realtime audio, computer use mode, experts mode (chain specialists), MCP server integration | Multi-mode agent operation, MCP integration |

### D. Knowledge Management + AI

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **Obsidian** | obsidian.md | Local-first Markdown, 2,700+ plugins, canvas/whiteboard, Copilot plugin (chat with vault), PDF annotation, Zotero integration | Plugin ecosystem, local-first philosophy, canvas for visual thinking |
| **Heptabase** | heptabase.com | Infinite whiteboard for spatial note arrangement, visual mind mapping, PDF annotation with AI chat, card-based atomic notes | Spatial/visual thinking paradigm beyond list-based PKM |
| **Tana** | tana.inc | Supertags (custom schemas for objects), AI auto-tagging, meeting transcription with summarization, schema-driven AI | Typed/structured data model that AI can reason over |
| **Anytype** | anytype.io | Object-based PKM, E2E encryption, P2P syncing, full data portability | Privacy-first architecture, data sovereignty |

### E. AI Companions with Emotional Systems

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **Replika** | replika.ai | Long-term relationship memory (references past conversations after weeks), emotional progression, AR/VR avatars, shared activities (games, meditation), mood tracking | Long-term emotional memory referencing, shared activities |
| **Nomi.ai** | nomi.ai | Three-layer memory, "chain of introspection" (human-like memory access), up to 10 companions with group chats, voice with emotional tone variation, adaptive communication style | Three-layer memory is closest to Letta's architecture, emotional voice variation |
| **Pi** (Inflection AI) | pi.ai | EQ-first design philosophy, voice with emotional intonation (pauses, breathing, laughter), five conversation modes, completely free | EQ-first design (not bolted on), emotional voice quality |

### F. Computer Use / OS Control AI Agents

| Product | URL | Key Features | What Rio Can Learn |
|---------|-----|--------------|-------------------|
| **Anthropic Computer Use** | anthropic.com | Vision-based desktop control (screenshot analysis), zoom capability, continuous feedback loop | Vision-based desktop control API |
| **Open Interpreter** | openinterpreter.com | Conversational computer control, local-first, desktop agent mode (document editing, PDF forms, multi-app workflows) | Conversational OS control patterns |
| **Browser Use** | github.com/browser-use/browser-use | Fine-tuned Browser Use 2.0 model, Playwright integration, DOM parsing + vision hybrid | Purpose-built browser automation model |

---

## 2. Rio's Position

### Existing Strengths (Rare/Unique)

- **Dual-retrieval RAG** (Qdrant vectors + Neo4j graph) -- most competitors have one or the other
- **Emotional engine** with mood, affinity, relationship tiers -- no productivity tool has this
- **Multi-agent supervisor with planner layer** -- most use simpler single-agent patterns
- **Combined study + productivity + OS control** in one self-hosted platform
- **Full-stack self-hosted** (FastAPI + Next.js) with privacy control

### Critical Gaps

| Gap | Impact | Competitors With It |
|-----|--------|-------------------|
| No spaced repetition / flashcards | Critical -- disqualifies as "study agent" | Quizlet, NotebookLM, Anki, RemNote |
| No MCP protocol support | Strategic -- locked out of ecosystem | PyGPT, OpenClaw, Cursor, all major platforms |
| No scheduled autonomous execution | High -- agent is purely reactive | Khoj, OpenClaw, Taskade |
| No voice / audio content | High -- missing highest-engagement format | NotebookLM, Pi, Nomi.ai |
| No calendar integration | Medium -- can't schedule-aware | Motion, Reclaim.ai, Notion |
| No vision input | Medium -- can't process images | Khanmigo, Anthropic Computer Use |
| No adaptive difficulty | Medium -- generic study sessions | Duolingo Birdbrain |

---

## 3. Development Roadmap Overview

```
Layer 0 (CURRENT) ── Stabilize foundation
         │
Layer 1  ── Quick Wins (3-5 weeks)
         │   ├── 1.1 Contextual Note Resurfacing
         │   ├── 1.2 Flashcards Phase 1 (SM-2)
         │   └── 1.3 Scheduled Automations
         │
Layer 2  ── Infrastructure Extensions (4-8 weeks)
         │   ├── 2.1 MCP Protocol Support
         │   ├── 2.2 Audio Overview / Podcast Generation
         │   └── 2.3 Adaptive Flashcards (Phase 2)
         │
Layer 3  ── Differentiation Features (8-16 weeks)
         │   ├── 3.1 Deep Research Mode
         │   ├── 3.2 Vision-based Input
         │   ├── 3.3 Calendar Integration
         │   ├── 3.4 Temporal Knowledge Graph
         │   └── 3.5 Emotional Voice
         │
Layer 4  ── Advanced Platform (long-term)
             ├── 4.1 Tiered Memory Architecture
             ├── 4.2 Self-Development Engine
             └── 4.3 Cross-Tool Integration via MCP
```

**Discipline**: No layer starts until the previous layer is stable and used daily. No scope expansion mid-layer.

---

## 4. Layer 1: Quick Wins on Existing Infrastructure

> Prerequisites: Layer 0 complete (sub-agents pass smoke tests, SSE streaming stable, memory works across sessions)

---

### 1.1 Contextual Note Resurfacing

**What**: Auto-surface relevant past notes in the chat sidebar when the user's conversation topic matches existing notes. Inspired by Mem.ai's "Heads Up" feature.

**Why**: Rio already has `NoteKnowledgeTool.search_notes()` and Neo4j graph traversal. This is the lowest-effort, highest-differentiation feature -- it uses existing infrastructure to deliver a novel experience no competitor with Rio's emotional awareness has.

**User Experience**: When a user asks "explain gradient descent", notes they've previously written about calculus, neural networks, or ML automatically appear as collapsible cards in the chat sidebar.

#### Implementation Steps

##### Step 1: Backend -- Add contextual search function

**File**: `src/workflows/tools/note_tools.py`

Add a new function (not a `@tool` -- this is called internally, not by the agent):

```python
def find_contextual_notes(
    query: str,
    user_id: str,
    k: int = 3,
    score_threshold: float = 0.6,
) -> list[dict]:
    """
    Search for notes semantically relevant to the current conversation.
    Returns lightweight note summaries (id, title, snippet, score).
    Called from the post-process node, not as an agent tool.
    """
    SessionFactory = get_session_factory()
    with SessionFactory() as db:
        tool_instance = NoteKnowledgeTool(db)
        raw = tool_instance.search_notes(query, user_id, k=k)

    # Parse JSON result from NoteKnowledgeTool
    results = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(results, list):
        return []

    # Filter by score threshold and return lightweight summaries
    contextual = []
    for note in results:
        score = note.get("score", 0)
        if score >= score_threshold:
            contextual.append({
                "id": note.get("id"),
                "title": note.get("title", "Untitled"),
                "snippet": (note.get("content", ""))[:200],
                "score": round(score, 3),
                "created_at": note.get("created_at"),
            })

    return contextual[:k]
```

##### Step 2: Backend -- Emit SSE event from post-process node

**File**: `src/workflows/react_graph.py`

In `_run_background_tasks()`, after the existing memory storage and emotional engine calls, add contextual note fetching. Since background tasks run in a thread, the results need to be emitted via a callback or stored in state.

**Alternative approach** (simpler): Add a new graph node `_contextual_notes_node` between the agent and post-process nodes, or call it directly in the streaming handler.

**Recommended approach**: Add to the SSE streaming generator in `src/routers/chat.py`:

```python
# In the streaming generator, after workflow completes but before _finish_message:

from workflows.tools.note_tools import find_contextual_notes

# Extract the user's question from the request
contextual = find_contextual_notes(
    query=question,
    user_id=str(user.id),
    k=3,
    score_threshold=0.6,
)
if contextual:
    yield _data_event("contextual-notes", {"notes": contextual})
```

**File**: `src/routers/chat.py`

The `_data_event()` helper already exists and produces:
```
data: {"type":"data-contextual-notes","data":{"notes":[...]}}\n\n
```

##### Step 3: Frontend -- Parse new SSE event

**File**: `apps/web/src/features/chat/lib/chat-transport.ts`

In the `dispatchCustomEvents()` function, add a handler for `data-contextual-notes`:

```typescript
// Inside the event type switch in dispatchCustomEvents():
} else if (type === 'data-contextual-notes') {
  const { notes } = evt.data ?? {}
  if (Array.isArray(notes) && notes.length > 0) {
    useChatStore.getState().setContextualNotes(notes)
  }
}
```

##### Step 4: Frontend -- Add store state

**File**: `apps/web/src/features/chat/store.ts`

Add to the chat store:

```typescript
interface ContextualNote {
  id: string
  title: string
  snippet: string
  score: number
  created_at: string
}

// In store state:
contextualNotes: ContextualNote[]

// In store actions:
setContextualNotes: (notes: ContextualNote[]) => void
clearContextualNotes: () => void
```

##### Step 5: Frontend -- Render sidebar cards

**File**: `apps/web/src/features/chat/components/ContextualNotesSidebar.tsx` (new)

Create a collapsible card component that displays in the chat sidebar (Workspace tab or a new "Context" tab):

```typescript
// Renders contextualNotes from the chat store
// Each card shows: title, snippet (first 200 chars), relevance score badge
// Clicking a card navigates to /notes with the note selected
// Cards fade in with framer-motion
// Clear button to dismiss all
```

Integrate into the existing sidebar layout at `apps/web/src/components/layout/sidebar.tsx`.

#### Verification

- [ ] Unit test: Given a user message and existing notes in the DB, `find_contextual_notes()` returns semantically relevant notes with scores above threshold
- [ ] Unit test: Notes below `score_threshold` are filtered out
- [ ] Integration test: Send a chat message via SSE → verify `data-contextual-notes` event fires in the stream
- [ ] Frontend test: Mock SSE event → verify `contextualNotes` state updates → verify sidebar renders cards
- [ ] Manual test: Create 3 notes about "machine learning", send a chat message about "neural networks" → verify related notes surface

---

### 1.2 Spaced Repetition / Flashcard System (Phase 1)

**What**: Generate flashcards from notes and conversation content. Use the SM-2 algorithm for scheduling reviews. Core CRUD + review UI.

**Why**: Spaced repetition is the #1 evidence-backed study technique. Every study competitor (Quizlet, Anki, RemNote, NotebookLM) has it. Without this, Rio cannot credibly position as a study agent. Rio's eventual differentiation (Layer 2.3): the emotional engine adjusts sessions based on mood/relationship tier.

#### Implementation Steps

##### Step 1: Database Models

**File**: `src/models/flashcard.py` (new)

```python
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Float, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class FlashcardSource(str, Enum):
    AGENT = "agent"
    USER = "user"


class Flashcard(Base, TimestampMixin):
    __tablename__ = "flashcard"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deck_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flashcard_deck.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note.id", ondelete="SET NULL"),
        nullable=True,
    )

    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)

    # SM-2 Algorithm fields
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Metadata
    source: Mapped[str] = mapped_column(
        SQLEnum(FlashcardSource, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=FlashcardSource.USER,
    )
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Stats
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    deck = relationship("FlashcardDeck", back_populates="flashcards")
    note = relationship("Note", foreign_keys=[note_id])

    __table_args__ = (
        Index("ix_flashcard_user_next_review", "user_id", "next_review"),
        Index("ix_flashcard_deck_next_review", "deck_id", "next_review"),
    )
```

**File**: `src/models/flashcard_deck.py` (new)

```python
from uuid import uuid4

from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base, TimestampMixin


class FlashcardDeck(Base, TimestampMixin):
    __tablename__ = "flashcard_deck"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    flashcards = relationship(
        "Flashcard", back_populates="deck", cascade="all, delete-orphan"
    )
```

##### Step 2: Alembic Migration

**File**: `src/infrastructure/database/migrations/versions/006_create_flashcard_tables.py` (new)

```python
"""Create flashcard and flashcard_deck tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006_create_flashcard_tables"
down_revision = "005_fix_note_thread_fk"  # Update to actual latest revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum
    source_enum = sa.Enum("agent", "user", name="flashcardsource")
    source_enum.create(op.get_bind(), checkfirst=True)

    # Deck table first (referenced by flashcard FK)
    op.create_table(
        "flashcard_deck",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # Flashcard table
    op.create_table(
        "flashcard",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("deck_id", UUID(as_uuid=True),
                  sa.ForeignKey("flashcard_deck.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("note_id", UUID(as_uuid=True),
                  sa.ForeignKey("note.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("front", sa.Text, nullable=False),
        sa.Column("back", sa.Text, nullable=False),
        sa.Column("ease_factor", sa.Float, nullable=False, default=2.5),
        sa.Column("interval_days", sa.Integer, nullable=False, default=0),
        sa.Column("repetitions", sa.Integer, nullable=False, default=0),
        sa.Column("next_review", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("source", source_enum, nullable=False, default="user"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_suspended", sa.Boolean, nullable=False, default=False),
        sa.Column("total_reviews", sa.Integer, nullable=False, default=0),
        sa.Column("correct_count", sa.Integer, nullable=False, default=0),
        sa.Column("streak", sa.Integer, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # Composite indexes
    op.create_index("ix_flashcard_user_next_review", "flashcard",
                    ["user_id", "next_review"])
    op.create_index("ix_flashcard_deck_next_review", "flashcard",
                    ["deck_id", "next_review"])


def downgrade() -> None:
    op.drop_index("ix_flashcard_deck_next_review")
    op.drop_index("ix_flashcard_user_next_review")
    op.drop_table("flashcard")
    op.drop_table("flashcard_deck")
    sa.Enum(name="flashcardsource").drop(op.get_bind(), checkfirst=True)
```

##### Step 3: Pydantic Schemas

**File**: `src/schemas/flashcard.py` (new)

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import List, Optional


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
    description: str
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
    tags: List[str]
    is_suspended: bool
    total_reviews: int
    correct_count: int
    streak: int
    created_at: datetime
    updated_at: datetime


# ── Review Schemas ──

class ReviewSubmit(BaseModel):
    """SM-2 quality rating: 0-5
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


class GenerateFromConversationRequest(BaseModel):
    thread_id: str
    deck_id: str
    max_cards: int = Field(10, ge=1, le=50)


# ── Stats ──

class FlashcardStats(BaseModel):
    total_cards: int
    due_today: int
    reviewed_today: int
    accuracy_7d: float
    current_streak: int
    cards_by_deck: dict
```

##### Step 4: Repository

**File**: `src/repositories/flashcard_repository.py` (new)

```python
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

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

    # ── Review Operations ──

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
                Flashcard.is_suspended == False,
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
            Flashcard.is_suspended == False,
            Flashcard.next_review <= now,
        )
        if deck_id:
            q = q.filter(Flashcard.deck_id == deck_id)
        return q.scalar() or 0

    def count_by_deck(self, deck_id: UUID) -> int:
        return (
            self.db.query(func.count(Flashcard.id))
            .filter(Flashcard.deck_id == deck_id)
            .scalar() or 0
        )
```

##### Step 5: Service with SM-2 Algorithm

**File**: `src/services/flashcard_service.py` (new)

```python
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from models.flashcard import Flashcard, FlashcardSource
from models.flashcard_deck import FlashcardDeck
from repositories.flashcard_repository import FlashcardRepository
from schemas.flashcard import (
    DeckCreate, DeckUpdate, DeckInDB,
    FlashcardCreate, FlashcardUpdate, FlashcardInDB,
    ReviewSubmit, ReviewResult, FlashcardStats,
)
from utils.logger import log_info, log_warning


class FlashcardService:
    def __init__(self, repo: FlashcardRepository) -> None:
        self._repo = repo

    # ── SM-2 Algorithm ──

    @staticmethod
    def sm2_update(
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval_days: int,
    ) -> Tuple[int, float, int]:
        """
        SM-2 spaced repetition algorithm.

        Args:
            quality: User rating 0-5 (0=blackout, 5=perfect)
            repetitions: Current repetition count
            ease_factor: Current ease factor (>= 1.3)
            interval_days: Current interval in days

        Returns:
            (new_repetitions, new_ease_factor, new_interval_days)
        """
        # Failed review (quality < 3): reset to beginning
        if quality < 3:
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

        return new_repetitions, new_ease, new_interval

    # ── Deck CRUD ──

    def list_decks(self, user_id: UUID) -> List[DeckInDB]:
        decks = self._repo.list_decks(user_id)
        result = []
        for d in decks:
            card_count = self._repo.count_by_deck(d.id)
            due_count = self._repo.count_due(user_id, d.id)
            result.append(DeckInDB(
                id=d.id, user_id=d.user_id, name=d.name,
                description=d.description or "",
                flashcard_count=card_count, due_count=due_count,
                created_at=d.created_at, updated_at=d.updated_at,
            ))
        return result

    def create_deck(self, user_id: UUID, data: DeckCreate) -> DeckInDB:
        deck = FlashcardDeck(
            id=uuid4(), user_id=user_id,
            name=data.name, description=data.description,
        )
        deck = self._repo.create_deck(deck)
        return DeckInDB(
            id=deck.id, user_id=deck.user_id, name=deck.name,
            description=deck.description or "",
            flashcard_count=0, due_count=0,
            created_at=deck.created_at, updated_at=deck.updated_at,
        )

    def delete_deck(self, user_id: UUID, deck_id: UUID) -> bool:
        return self._repo.delete_deck(deck_id, user_id)

    # ── Flashcard CRUD ──

    def list_cards(
        self, user_id: UUID, deck_id: Optional[UUID] = None,
        limit: int = 50, offset: int = 0,
    ) -> List[FlashcardInDB]:
        cards = self._repo.list_cards(user_id, deck_id, limit, offset)
        return [FlashcardInDB.model_validate(c) for c in cards]

    def create_card(self, user_id: UUID, data: FlashcardCreate) -> FlashcardInDB:
        card = Flashcard(
            id=uuid4(), user_id=user_id,
            deck_id=UUID(data.deck_id),
            note_id=UUID(data.note_id) if data.note_id else None,
            front=data.front, back=data.back,
            tags=data.tags,
            source=FlashcardSource(data.source),
        )
        card = self._repo.create_card(card)
        return FlashcardInDB.model_validate(card)

    def create_cards_bulk(
        self, user_id: UUID, cards_data: List[FlashcardCreate],
    ) -> List[FlashcardInDB]:
        cards = []
        for data in cards_data:
            cards.append(Flashcard(
                id=uuid4(), user_id=user_id,
                deck_id=UUID(data.deck_id),
                note_id=UUID(data.note_id) if data.note_id else None,
                front=data.front, back=data.back,
                tags=data.tags,
                source=FlashcardSource(data.source),
            ))
        created = self._repo.create_cards_bulk(cards)
        return [FlashcardInDB.model_validate(c) for c in created]

    def delete_card(self, user_id: UUID, card_id: UUID) -> bool:
        return self._repo.delete_card(card_id, user_id)

    # ── Review ──

    def get_due_cards(
        self, user_id: UUID, deck_id: Optional[UUID] = None, limit: int = 20,
    ) -> List[FlashcardInDB]:
        cards = self._repo.get_due_cards(user_id, deck_id, limit)
        return [FlashcardInDB.model_validate(c) for c in cards]

    def submit_review(self, user_id: UUID, review: ReviewSubmit) -> Optional[ReviewResult]:
        card = self._repo.get_card(UUID(review.card_id), user_id)
        if not card:
            return None

        # Run SM-2
        new_reps, new_ease, new_interval = self.sm2_update(
            quality=review.quality,
            repetitions=card.repetitions,
            ease_factor=card.ease_factor,
            interval_days=card.interval_days,
        )

        now = datetime.now(timezone.utc)
        is_correct = review.quality >= 3

        # Update card
        card.repetitions = new_reps
        card.ease_factor = new_ease
        card.interval_days = new_interval
        card.next_review = now + timedelta(days=new_interval)
        card.total_reviews += 1
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

    # ── AI Generation ──

    def generate_from_note(
        self, user_id: UUID, note_id: UUID, deck_id: UUID, max_cards: int = 10,
    ) -> List[FlashcardInDB]:
        """
        Use LLM to generate flashcards from note content.
        """
        from core.dependencies import get_session_factory
        from models.note import Note

        SessionFactory = get_session_factory()
        with SessionFactory() as db:
            note = db.query(Note).filter(
                Note.id == note_id, Note.user_id == user_id
            ).first()
            if not note:
                log_warning(f"Note {note_id} not found for flashcard generation")
                return []
            note_content = f"# {note.title}\n\n{note.content}"

        # LLM call to generate Q/A pairs
        from infrastructure.llm.model_form import SELECTED_MODEL
        if not SELECTED_MODEL or not getattr(SELECTED_MODEL, "llm", None):
            SELECTED_MODEL.setup()

        prompt = f"""Extract up to {max_cards} key concepts from this note and create flashcards.
Return ONLY a JSON array of objects with "front" (question) and "back" (answer) keys.
Keep questions specific and answers concise but complete.

Note content:
{note_content}

JSON array:"""

        response = SELECTED_MODEL.llm.invoke(prompt)
        import json
        try:
            pairs = json.loads(response.content)
        except (json.JSONDecodeError, AttributeError):
            log_warning("Failed to parse LLM flashcard generation output")
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

        return self.create_cards_bulk(user_id, cards_data)

    # ── Stats ──

    def get_stats(self, user_id: UUID) -> FlashcardStats:
        from datetime import date
        today_start = datetime.combine(date.today(), datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

        all_cards = self._repo.list_cards(user_id, limit=10000)
        due = self._repo.count_due(user_id)

        reviewed_today = sum(
            1 for c in all_cards
            if c.total_reviews > 0 and c.updated_at >= today_start
        )

        # 7-day accuracy
        recent = [c for c in all_cards if c.total_reviews > 0]
        if recent:
            total_correct = sum(c.correct_count for c in recent)
            total_reviews = sum(c.total_reviews for c in recent)
            accuracy = total_correct / total_reviews if total_reviews > 0 else 0.0
        else:
            accuracy = 0.0

        # Cards by deck
        deck_counts: dict = {}
        for c in all_cards:
            dk = str(c.deck_id)
            deck_counts[dk] = deck_counts.get(dk, 0) + 1

        max_streak = max((c.streak for c in all_cards), default=0)

        return FlashcardStats(
            total_cards=len(all_cards),
            due_today=due,
            reviewed_today=reviewed_today,
            accuracy_7d=round(accuracy, 3),
            current_streak=max_streak,
            cards_by_deck=deck_counts,
        )
```

##### Step 6: Router

**File**: `src/routers/flashcard.py` (new)

```python
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user
from core.exceptions import NotFoundError
from models.user import User
from schemas.flashcard import (
    DeckCreate, DeckInDB,
    FlashcardCreate, FlashcardInDB,
    ReviewSubmit, ReviewResult,
    GenerateFromNoteRequest, FlashcardStats,
)
from services.flashcard_service import FlashcardService
from repositories.flashcard_repository import FlashcardRepository

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _get_service(db=Depends(...)):  # Wire via dependencies.py
    return FlashcardService(FlashcardRepository(db))


# ── Decks ──

@router.get("/decks", response_model=List[DeckInDB])
async def list_decks(
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(svc.list_decks, user.id)


@router.post("/decks", response_model=DeckInDB, status_code=status.HTTP_201_CREATED)
async def create_deck(
    body: DeckCreate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(svc.create_deck, user.id, body)


@router.delete("/decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: UUID,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
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
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(
        svc.list_cards, user.id, deck_id, limit, offset
    )


@router.post("/cards", response_model=FlashcardInDB, status_code=status.HTTP_201_CREATED)
async def create_card(
    body: FlashcardCreate,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(svc.create_card, user.id, body)


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: UUID,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    ok = await concurrency_manager.run_in_thread(svc.delete_card, user.id, card_id)
    if not ok:
        raise NotFoundError("Card not found")


# ── Review ──

@router.get("/due", response_model=List[FlashcardInDB])
async def get_due_cards(
    deck_id: Optional[UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(
        svc.get_due_cards, user.id, deck_id, limit
    )


@router.post("/review", response_model=ReviewResult)
async def submit_review(
    body: ReviewSubmit,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    result = await concurrency_manager.run_in_thread(svc.submit_review, user.id, body)
    if not result:
        raise NotFoundError("Card not found")
    return result


# ── Generation ──

@router.post("/generate/note", response_model=List[FlashcardInDB])
async def generate_from_note(
    body: GenerateFromNoteRequest,
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(
        svc.generate_from_note, user.id,
        UUID(body.note_id), UUID(body.deck_id), body.max_cards,
    )


# ── Stats ──

@router.get("/stats", response_model=FlashcardStats)
async def get_stats(
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(svc.get_stats, user.id)
```

##### Step 7: Wire into dependency injection

**File**: `src/core/dependencies.py` (modify)

Add:
```python
def get_flashcard_repository(db: Session = Depends(get_db)) -> FlashcardRepository:
    from repositories.flashcard_repository import FlashcardRepository
    return FlashcardRepository(db)

def get_flashcard_service(
    repo: FlashcardRepository = Depends(get_flashcard_repository),
) -> FlashcardService:
    from services.flashcard_service import FlashcardService
    return FlashcardService(repo)
```

**File**: `src/routers/__init__.py` or `src/core/app.py` (modify)

Register the router:
```python
from routers.flashcard import router as flashcard_router
app.include_router(flashcard_router, prefix="/api/v1")
```

##### Step 8: Agent Integration -- Tool Registry

**File**: `src/workflows/tool_registry.py` (modify)

Add entry to `_TOOL_ENTRIES`:
```python
"delegate_flashcard_task": {
    "description": "Delegate flashcard/study-card operations (create, generate from notes, review, list decks). Use when user wants to study, make flashcards, quiz themselves, or review.",
    "guide": """## Tool: delegate_flashcard_task

### Purpose
Handle all flashcard and spaced repetition operations.

### Operations
- **generate**: Create flashcards from a note ("make flashcards from my notes about X")
- **review**: Start a review session ("quiz me", "review flashcards")
- **list**: Show decks and cards ("show my flashcard decks")
- **create**: Create individual cards ("add a flashcard: Q: ... A: ...")
- **stats**: Show study statistics ("how am I doing with flashcards?")

### Instruction Format
Pass a natural language instruction describing what the user wants.
Include note_id or deck_id if the user referenced a specific note or deck.

### Examples
- "Generate 10 flashcards from note abc-123 into deck xyz-456"
- "Show all due flashcards for today"
- "Create a new deck called 'Biology Chapter 5'"
""",
},
```

##### Step 9: Agent Integration -- Delegation Tool

**File**: `src/workflows/tools/delegation_tools.py` (modify)

Add to `build_delegation_tools()`:
```python
@tool
def delegate_flashcard_task(instruction: str) -> str:
    """Delegate flashcard/study-card operations to Flashcard Agent.
    Use for creating, generating, reviewing flashcards and managing decks."""
    log_info(f"[Delegation] -> Flashcard Agent: {instruction[:100]}")
    return _invoke_sub_agent(_get_agent("flashcard"), instruction)
```

Add `"flashcard"` to the `builders` dict:
```python
builders = {
    "mission": lambda uid: build_mission_sub_agent(uid),
    "note": lambda uid: build_note_sub_agent(uid),
    "flashcard": lambda uid: build_flashcard_sub_agent(uid),
    # ...
}
```

##### Step 10: Agent Integration -- Sub-Agent

**File**: `src/workflows/tools/sub_agents.py` (modify)

Add:
```python
_FLASHCARD_AGENT_PROMPT = """\
You are a flashcard management agent.

Rules:
- For generating flashcards from a note, call generate_flashcards_from_note with the note_id and deck_id.
- For listing due cards, call get_due_flashcards.
- For listing decks, call list_flashcard_decks.
- For creating cards manually, call create_flashcard with front/back text.
- Always confirm what you created/modified in your response.
- Return a concise summary of the action taken.
"""

def build_flashcard_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for flashcard operations."""
    from workflows.tools.flashcard_tools import build_flashcard_tools

    tools = build_flashcard_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_FLASHCARD_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built flashcard agent with {len(tools)} tools")
    return agent
```

##### Step 11: Agent Integration -- Flashcard Tools

**File**: `src/workflows/tools/flashcard_tools.py` (new)

```python
import json
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from core.dependencies import get_session_factory
from repositories.flashcard_repository import FlashcardRepository
from services.flashcard_service import FlashcardService
from schemas.flashcard import (
    DeckCreate, FlashcardCreate, ReviewSubmit,
    GenerateFromNoteRequest,
)


def build_flashcard_tools(user_id: str) -> list:
    SessionFactory = get_session_factory()

    def _svc() -> FlashcardService:
        db = SessionFactory()
        return FlashcardService(FlashcardRepository(db))

    @tool
    def list_flashcard_decks() -> str:
        """List all flashcard decks with card counts and due counts."""
        svc = _svc()
        decks = svc.list_decks(UUID(user_id))
        return json.dumps([d.model_dump(mode="json") for d in decks], default=str)

    @tool
    def create_flashcard_deck(name: str, description: str = "") -> str:
        """Create a new flashcard deck."""
        svc = _svc()
        deck = svc.create_deck(UUID(user_id), DeckCreate(name=name, description=description))
        return json.dumps(deck.model_dump(mode="json"), default=str)

    @tool
    def get_due_flashcards(deck_id: Optional[str] = None, limit: int = 20) -> str:
        """Get flashcards due for review today."""
        svc = _svc()
        cards = svc.get_due_cards(
            UUID(user_id),
            UUID(deck_id) if deck_id else None,
            limit,
        )
        return json.dumps([c.model_dump(mode="json") for c in cards], default=str)

    @tool
    def create_flashcard(deck_id: str, front: str, back: str, tags: str = "") -> str:
        """Create a single flashcard manually.
        Args:
            deck_id: UUID of the deck
            front: Question text
            back: Answer text
            tags: Comma-separated tags (optional)
        """
        svc = _svc()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        card = svc.create_card(
            UUID(user_id),
            FlashcardCreate(deck_id=deck_id, front=front, back=back, tags=tag_list),
        )
        return json.dumps(card.model_dump(mode="json"), default=str)

    @tool
    def generate_flashcards_from_note(note_id: str, deck_id: str, max_cards: int = 10) -> str:
        """Generate flashcards from a note using AI.
        Args:
            note_id: UUID of the source note
            deck_id: UUID of the target deck
            max_cards: Maximum number of cards to generate (default 10)
        """
        svc = _svc()
        cards = svc.generate_from_note(
            UUID(user_id), UUID(note_id), UUID(deck_id), max_cards,
        )
        return json.dumps(
            {"generated": len(cards), "cards": [c.model_dump(mode="json") for c in cards]},
            default=str,
        )

    @tool
    def get_flashcard_stats() -> str:
        """Get flashcard study statistics (total cards, due today, accuracy, streak)."""
        svc = _svc()
        stats = svc.get_stats(UUID(user_id))
        return json.dumps(stats.model_dump(), default=str)

    return [
        list_flashcard_decks,
        create_flashcard_deck,
        get_due_flashcards,
        create_flashcard,
        generate_flashcards_from_note,
        get_flashcard_stats,
    ]
```

##### Step 12: Frontend -- Next.js API Routes

**File**: `apps/web/src/app/api/flashcards/route.ts` (new)
**File**: `apps/web/src/app/api/flashcards/decks/route.ts` (new)
**File**: `apps/web/src/app/api/flashcards/due/route.ts` (new)
**File**: `apps/web/src/app/api/flashcards/review/route.ts` (new)
**File**: `apps/web/src/app/api/flashcards/generate/note/route.ts` (new)
**File**: `apps/web/src/app/api/flashcards/stats/route.ts` (new)

Follow the same proxy pattern used by existing routes (e.g., `apps/web/src/app/api/notes/route.ts`): forward requests to the FastAPI backend with auth token.

##### Step 13: Frontend -- Feature Slice

**Directory**: `apps/web/src/features/flashcards/` (new)

Create the standard feature slice:
- `api.ts` -- API client functions (`apiListDecks`, `apiGetDueCards`, `apiSubmitReview`, `apiGenerateFromNote`, `apiGetStats`)
- `types.ts` -- TypeScript interfaces (`FlashcardRecord`, `DeckRecord`, `ReviewResult`, `FlashcardStats`)
- `store.ts` -- Zustand store (decks, cards, due cards, current session state, review history)
- `components/FlashcardReview.tsx` -- Card flip animation, quality rating (0-5), next review display
- `components/DeckList.tsx` -- Deck management grid
- `components/DeckEditor.tsx` -- Create/edit deck modal
- `components/StudySession.tsx` -- Review session with progress bar, streak counter
- `components/FlashcardStats.tsx` -- Statistics dashboard (accuracy chart, due forecast)

##### Step 14: Frontend -- Page

**File**: `apps/web/src/app/flashcards/page.tsx` (new)

Main flashcards page with:
- Deck list with due-card badges
- "Start Review" button per deck
- Stats overview
- "Generate from Note" action

##### Step 15: Frontend -- Navigation

**File**: `apps/web/src/components/layout/sidebar.tsx` (modify)

Add flashcards nav item with due-count badge (similar to existing mission/notes items).

#### Verification

- [ ] Unit test: SM-2 algorithm produces correct intervals for all quality ratings (0-5)
  - quality=5, first review → interval=1, reps=1
  - quality=5, second review → interval=6, reps=2
  - quality=5, third review → interval=round(6*2.5)=15, reps=3
  - quality=2 (fail) → interval=1, reps=0, ease reduced
- [ ] Unit test: `generate_from_note` produces valid FlashcardCreate objects from LLM output
- [ ] Integration test: Create deck → create card → mark due → submit review → verify interval updated
- [ ] Integration test: Create note → generate flashcards from note → verify cards linked to note
- [ ] Agent routing test: Message "make flashcards from my last note" → planner routes to `delegate_flashcard_task`
- [ ] Frontend test: Review session flow → flip card → rate → next card → session summary

---

### 1.3 Scheduled Automations

**What**: Cron-based autonomous agent execution. Daily study reminders, weekly knowledge reviews, scheduled flashcard review notifications.

**Why**: This is the bridge between reactive chat and proactive agent behavior. Khoj and OpenClaw both have this. It also enables the spaced repetition system to send "cards due" reminders and the contextual resurfacing to send daily knowledge digests.

#### Implementation Steps

##### Step 1: Database Model

**File**: `src/models/automation.py` (new)

```python
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class AutomationDelivery(str, Enum):
    CHAT_THREAD = "chat_thread"
    NOTE = "note"
    NOTIFICATION = "notification"


class Automation(Base, TimestampMixin):
    __tablename__ = "automation"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")

    # Schedule
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")

    # Agent instruction
    agent_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    agent_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="chat")

    # Delivery
    result_delivery: Mapped[str] = mapped_column(
        SQLEnum(AutomationDelivery, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AutomationDelivery.NOTIFICATION,
    )

    # State
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_runs: Mapped[int] = mapped_column(Integer, nullable=True)  # None = unlimited
    last_result: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_automation_user_enabled", "user_id", "enabled"),
        Index("ix_automation_next_run", "next_run_at"),
    )
```

##### Step 2: Alembic Migration

**File**: `src/infrastructure/database/migrations/versions/007_create_automation_table.py` (new)

Follow the same pattern as Step 2 in section 1.2. Create `automation` table with all columns and indexes.

##### Step 3: Schema

**File**: `src/schemas/automation.py` (new)

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional


class AutomationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)
    cron_expression: str = Field(..., max_length=100)
    timezone: str = Field("UTC", max_length=50)
    agent_instruction: str = Field(..., max_length=10000)
    agent_mode: str = Field("chat")
    result_delivery: str = Field("notification")
    max_runs: Optional[int] = Field(None, ge=1)


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    agent_instruction: Optional[str] = None
    enabled: Optional[bool] = None
    max_runs: Optional[int] = None


class AutomationInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    agent_instruction: str
    agent_mode: str
    result_delivery: str
    enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    max_runs: Optional[int]
    last_result: Optional[dict]
    created_at: datetime
    updated_at: datetime
```

##### Step 4: Repository

**File**: `src/repositories/automation_repository.py` (new)

Standard CRUD following `BaseRepository` pattern. Key methods:
- `list_by_user(user_id, enabled_only=False)`
- `get_by_id(automation_id, user_id)`
- `get_due_automations()` -- query `enabled=True AND next_run_at <= now()`
- `create(automation)`
- `delete_by_id(automation_id, user_id)`

##### Step 5: Service

**File**: `src/services/automation_service.py` (new)

```python
from croniter import croniter
from datetime import datetime, timezone

class AutomationService:
    def __init__(self, repo: AutomationRepository) -> None:
        self._repo = repo

    def create_automation(self, user_id: UUID, data: AutomationCreate) -> AutomationInDB:
        # Validate cron expression
        if not croniter.is_valid(data.cron_expression):
            raise ValidationError(f"Invalid cron expression: {data.cron_expression}")

        now = datetime.now(timezone.utc)
        cron = croniter(data.cron_expression, now)
        next_run = cron.get_next(datetime)

        automation = Automation(
            id=uuid4(), user_id=user_id,
            name=data.name, description=data.description,
            cron_expression=data.cron_expression, timezone=data.timezone,
            agent_instruction=data.agent_instruction, agent_mode=data.agent_mode,
            result_delivery=AutomationDelivery(data.result_delivery),
            next_run_at=next_run,
            max_runs=data.max_runs,
        )
        return self._repo.create(automation)

    def get_due_automations(self) -> List[AutomationInDB]:
        return self._repo.get_due_automations()

    async def execute_automation(self, automation: Automation) -> dict:
        """Execute an automation by running the agent instruction through the workflow."""
        from workflows.executor import run_workflow
        from core.settings import AgentConfig
        from uuid import uuid4

        config = AgentConfig(mode=automation.agent_mode)
        thread_id = str(uuid4())

        result = run_workflow(
            question=automation.agent_instruction,
            config=config,
            history=[],
            thread_id=thread_id,
            user_id=str(automation.user_id),
        )

        # Update automation state
        now = datetime.now(timezone.utc)
        cron = croniter(automation.cron_expression, now)
        automation.last_run_at = now
        automation.next_run_at = cron.get_next(datetime)
        automation.run_count += 1
        automation.last_result = {
            "answer": result.get("answer", "")[:2000],
            "thread_id": thread_id,
            "executed_at": now.isoformat(),
        }

        # Check max_runs
        if automation.max_runs and automation.run_count >= automation.max_runs:
            automation.enabled = False

        self._repo.flush()

        # Deliver result based on delivery mode
        self._deliver_result(automation, result)

        return result
```

##### Step 6: Scheduler Background Task

**File**: `src/core/scheduler.py` (new)

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()


async def check_due_automations():
    """Check for and execute due automations. Runs every 60 seconds."""
    from core.dependencies import get_session_factory
    from repositories.automation_repository import AutomationRepository
    from services.automation_service import AutomationService

    SessionFactory = get_session_factory()
    with SessionFactory() as db:
        repo = AutomationRepository(db)
        svc = AutomationService(repo)
        due = svc.get_due_automations()

        for automation in due:
            try:
                await svc.execute_automation(automation)
            except Exception as e:
                log_warning(f"Automation {automation.id} failed: {e}")


def start_scheduler():
    scheduler.add_job(
        check_due_automations,
        trigger=IntervalTrigger(seconds=60),
        id="automation_checker",
        replace_existing=True,
    )
    scheduler.start()
```

**File**: `src/core/startup.py` (modify)

Add to `run_startup_tasks()`:
```python
from core.scheduler import start_scheduler
start_scheduler()
```

##### Step 7: Router

**File**: `src/routers/automation.py` (new)

Standard CRUD router following the pattern in `src/routers/note.py`:
- `GET /automations` -- list user's automations
- `POST /automations` -- create
- `PUT /automations/{id}` -- update
- `DELETE /automations/{id}` -- delete
- `POST /automations/{id}/run` -- manual trigger

##### Step 8: Frontend

**Directory**: `apps/web/src/features/automations/` (new)

- `api.ts`, `types.ts`, `store.ts`
- `components/AutomationList.tsx` -- list with enable/disable toggles
- `components/AutomationEditor.tsx` -- form with cron presets:
  - "Every morning at 9am" → `0 9 * * *`
  - "Every Monday" → `0 9 * * 1`
  - "Every hour" → `0 * * * *`
  - Custom cron input with human-readable preview

**Page**: `apps/web/src/app/automations/page.tsx` (new)

##### Step 9: Dependencies

Add to `pyproject.toml`:
```toml
apscheduler = ">=3.10"
croniter = ">=2.0"
```

#### Verification

- [ ] Unit test: Cron expression validation (valid/invalid expressions)
- [ ] Unit test: `next_run_at` calculation from cron expression
- [ ] Integration test: Create automation → advance clock → verify execution fires
- [ ] Integration test: Automation with `max_runs=1` → execute → verify `enabled=False`
- [ ] Integration test: Automation result delivered as note (delivery mode: note)
- [ ] Scheduler test: Mock due automations → verify `check_due_automations` processes them

---

## 5. Layer 2: Infrastructure Extensions

> Prerequisites: Layer 1 features stable and used daily

---

### 2.1 MCP Protocol Support (Client-side)

**What**: Make Rio an MCP client that can connect to 5,800+ existing MCP tool servers (Slack, Google Drive, Jira, Notion, GitHub, etc.) using the industry-standard Model Context Protocol.

**Why**: Instead of building individual integrations over months, MCP collapses this to configuration per connector. 97M+ monthly SDK downloads -- this is the "USB-C for AI" interoperability standard. Every major platform (Cursor, PyGPT, OpenClaw) supports it.

#### Implementation Steps

##### Step 1: MCP Client Module

**File**: `src/infrastructure/mcp/__init__.py` (new)
**File**: `src/infrastructure/mcp/client.py` (new)

```python
"""
MCP Client for connecting to external MCP tool servers.
Supports both stdio and SSE transports.
"""
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


class MCPClientManager:
    """Manages connections to multiple MCP servers."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, list] = {}

    async def connect_stdio(self, server_id: str, command: str, args: list[str]):
        """Connect to an MCP server via stdio transport."""
        ...

    async def connect_sse(self, server_id: str, url: str):
        """Connect to an MCP server via SSE transport."""
        ...

    async def list_tools(self, server_id: str) -> list[dict]:
        """List all tools from a connected server."""
        ...

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on a connected MCP server."""
        ...

    async def disconnect(self, server_id: str):
        """Disconnect from an MCP server."""
        ...
```

##### Step 2: MCP Tool Adapter

**File**: `src/infrastructure/mcp/tool_adapter.py` (new)

Converts MCP tool definitions into LangChain `@tool` functions:

```python
def mcp_tool_to_langchain(
    server_id: str,
    mcp_tool: dict,
    client_manager: MCPClientManager,
) -> Callable:
    """
    Convert an MCP tool definition into a LangChain @tool function.
    The returned function calls the MCP server when invoked by the agent.
    """
    name = mcp_tool["name"]
    description = mcp_tool.get("description", "")
    input_schema = mcp_tool.get("inputSchema", {})

    @tool(name=f"mcp_{server_id}_{name}", description=description)
    def mcp_tool_fn(**kwargs) -> str:
        import asyncio
        result = asyncio.run(
            client_manager.call_tool(server_id, name, kwargs)
        )
        return str(result)

    return mcp_tool_fn
```

##### Step 3: MCP Server Registry

**File**: `src/infrastructure/mcp/registry.py` (new)

Configuration and persistence of which MCP servers are available:

```python
@dataclass
class MCPServerConfig:
    id: str
    name: str
    transport: Literal["stdio", "sse"]
    command: Optional[str] = None      # For stdio
    args: list[str] = field(default_factory=list)
    url: Optional[str] = None          # For SSE
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    risk_tier: int = 2                 # Default: soft confirm
```

##### Step 4: Integration with Tool Registry

**File**: `src/workflows/tool_registry.py` (modify)

In `build_tool_registry()`, after building native tools, also load MCP tools:
```python
# After native tool registration:
mcp_tools = _load_mcp_tools(user_role)
for t in mcp_tools:
    registry[t.name] = ToolRegistryEntry(
        name=t.name, description=t.description,
        guide=t.guide, is_skill=False,
    )
```

##### Step 5: Integration with Tool Builder

**File**: `src/workflows/tools/__init__.py` (modify)

In `build_supervisor_tools()`, include MCP-adapted tools:
```python
# After building native tools:
from infrastructure.mcp.tool_adapter import get_mcp_langchain_tools
mcp_tools = get_mcp_langchain_tools()
all_tools.extend(mcp_tools)
```

##### Step 6: Router

**File**: `src/routers/mcp.py` (new)

- `GET /mcp/servers` -- list configured MCP servers
- `POST /mcp/servers` -- add a new MCP server connection
- `PUT /mcp/servers/{id}` -- update configuration
- `DELETE /mcp/servers/{id}` -- remove
- `GET /mcp/tools` -- list all tools from connected servers
- `POST /mcp/servers/{id}/test` -- test connection

##### Step 7: Frontend

Settings page for MCP server management:
- Server list with connection status indicators
- "Add Server" form (name, transport type, command/URL)
- Tool discovery: show available tools per connected server
- Enable/disable toggle per server

##### Step 8: Dependencies

Add to `pyproject.toml`:
```toml
mcp = ">=1.0"
```

#### Verification

- [ ] Unit test: MCP tool definition → LangChain tool conversion → correct function signature
- [ ] Integration test: Connect to mock MCP server → list tools → call tool → verify result
- [ ] Integration test: Planner sees MCP tools in descriptions → routes to MCP tool → agent invokes correctly
- [ ] Manual test: Connect to a real MCP server (e.g., filesystem) → ask Rio to use it → verify end-to-end

---

### 2.2 Audio Overview / Podcast Generation

**What**: Convert study materials (notes, document summaries, flashcard decks) into conversational audio overviews. Inspired by NotebookLM's killer feature.

**Why**: Audio is the highest-engagement study format. Rio's differentiation: the persona system means the audio sounds like Rio's character, not generic podcast hosts. Emotional state injection adjusts TTS parameters based on mood.

#### Implementation Steps

##### Step 1: Audio Overview Model

**File**: `src/models/audio_overview.py` (new)

```python
class AudioOverview(Base, TimestampMixin):
    __tablename__ = "audio_overview"

    id              # UUID PK
    user_id         # FK -> user
    title           # String(500)
    source_ids      # JSONB -- list of note/document IDs used
    source_type     # Enum: "notes", "documents", "flashcards"
    transcript      # Text -- the generated script
    audio_path      # String -- path to audio file in storage/
    duration_seconds  # Integer
    format          # Enum: "summary", "dialogue", "lecture"
    status          # Enum: "pending", "generating", "ready", "failed"
```

##### Step 2: Audio Service

**File**: `src/services/audio_service.py` (new)

```python
class AudioService:
    def generate_overview(
        self,
        user_id: UUID,
        source_ids: list[str],
        source_type: str,
        format: str = "summary",
    ) -> AudioOverview:
        """
        1. Fetch source content (notes, documents, flashcards)
        2. LLM call to generate conversational script using persona voice
        3. TTS synthesis of the script into audio
        4. Store audio file and persist metadata
        """

    def _generate_script(self, content: str, format: str, persona: dict) -> str:
        """
        Use LLM to convert source content into a conversational script.
        Injects persona voice from src/workflows/persona.py.
        """

    def _synthesize_audio(self, script: str, mood: str) -> tuple[str, int]:
        """
        Convert script to audio using TTS.
        MVP: OpenAI TTS API or Edge TTS (free).
        Later: Local Qwen3 TTS (plan section 23.5).
        Returns: (file_path, duration_seconds)
        """
```

**TTS Options** (in priority order for MVP):
1. `edge-tts` Python library (free, decent quality, no GPU)
2. OpenAI TTS API (paid, high quality)
3. Local Qwen3 TTS (future, requires GPU)

##### Step 3: Router

**File**: `src/routers/audio.py` (new)

- `POST /audio/generate` -- trigger async generation (returns job ID + status "pending")
- `GET /audio/{id}` -- get audio metadata and streaming URL
- `GET /audio/{id}/stream` -- stream audio file with range request support
- `GET /audio` -- list user's audio overviews
- `DELETE /audio/{id}` -- delete audio overview

##### Step 4: Frontend

Extend notes UI:
- "Generate Audio Overview" button on note detail page
- Audio player component (reuse `howler.js` infrastructure from music feature)
- Generation progress indicator (polling for status)

New `apps/web/src/features/audio/` feature slice with:
- `api.ts`, `types.ts`, `store.ts`
- `components/AudioPlayer.tsx` -- playback controls, transcript viewer
- `components/AudioList.tsx` -- list of generated overviews

##### Step 5: Dependencies

Add to `pyproject.toml`:
```toml
edge-tts = ">=6.0"
```

#### Verification

- [ ] Unit test: Script generation from note content (mock LLM, verify persona-driven script)
- [ ] Unit test: TTS synthesis produces valid audio file (mock TTS, verify file creation)
- [ ] Integration test: Create note → generate audio → verify status transitions (pending → generating → ready)
- [ ] Integration test: Audio streaming with range request support (partial content)
- [ ] Manual test: Listen to generated audio → verify quality and persona voice

---

### 2.3 Adaptive Flashcards (Phase 2)

**What**: Extend the flashcard system with emotional engine integration. Rio adjusts study sessions based on user's emotional state, inspired by Duolingo Birdbrain's adaptive difficulty.

**Why**: This is Rio's unique differentiator. No other flashcard system has an emotional engine that modifies behavior based on mood and relationship tier.

#### Implementation Steps

##### Step 1: Extend FlashcardService

**File**: `src/services/flashcard_service.py` (modify)

Add `adaptive_session()` method:

```python
def adaptive_session(
    self,
    user_id: UUID,
    deck_id: Optional[UUID] = None,
    max_cards: int = 20,
) -> dict:
    """
    Create an adaptive study session based on emotional state.

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
    from services.emotional_engine import EmotionalEngine
    from repositories.emotional_state_repository import EmotionalStateRepository

    # Get emotional context
    with get_db_context() as db:
        engine = EmotionalEngine(EmotionalStateRepository(db))
        emo = engine.compute_emotional_context(user_id, "rio")

    mood = emo.get("mood", "neutral")
    energy = float(emo.get("energy", "0.5"))
    tier = emo.get("affinity_tier", "acquaintance")

    # Adapt session parameters based on emotional state
    if mood in ("tired", "sad") or energy < 0.3:
        adjusted_max = min(max_cards, 8)
        difficulty_bias = "easy"
        encouragement = "gentle"      # More praise, shorter sessions
    elif mood in ("frustrated",):
        adjusted_max = min(max_cards, 5)
        difficulty_bias = "review_only"  # No new cards, only review
        encouragement = "supportive"
    elif mood in ("excited", "happy") and energy > 0.7:
        adjusted_max = max_cards
        difficulty_bias = "challenging"
        encouragement = "brief"       # Less hand-holding
    else:
        adjusted_max = max_cards
        difficulty_bias = "balanced"
        encouragement = "standard"

    # Get due cards with difficulty bias
    cards = self.get_due_cards(user_id, deck_id, adjusted_max)

    # Sort by difficulty bias
    if difficulty_bias == "easy":
        cards.sort(key=lambda c: c.ease_factor, reverse=True)
    elif difficulty_bias == "challenging":
        cards.sort(key=lambda c: c.ease_factor)

    return {
        "cards": cards,
        "session_config": {
            "max_cards": adjusted_max,
            "encouragement_style": encouragement,
            "difficulty_bias": difficulty_bias,
        },
        "emotional_context": emo,
    }
```

##### Step 2: Router Extension

**File**: `src/routers/flashcard.py` (modify)

Add endpoint:
```python
@router.get("/session", response_model=dict)
async def get_adaptive_session(
    deck_id: Optional[UUID] = Query(None),
    max_cards: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    svc: FlashcardService = Depends(_get_service),
):
    return await concurrency_manager.run_in_thread(
        svc.adaptive_session, user.id, deck_id, max_cards
    )
```

##### Step 3: Frontend -- Adaptive Study Session UI

Extend `apps/web/src/features/flashcards/components/StudySession.tsx`:
- Display mood-adaptive encouragement messages (pulled from session_config)
- Adjust UI colors/intensity based on emotional context
- Show gentler UI when mood is tired/sad (softer colors, bigger text)
- Show streak/challenge indicators when mood is excited

#### Verification

- [ ] Unit test: Tired mood → max 8 cards, easy bias, gentle encouragement
- [ ] Unit test: Frustrated mood → max 5 cards, review only, supportive
- [ ] Unit test: Excited + high energy → full cards, challenging, brief
- [ ] Integration test: Set emotional state → get adaptive session → verify card selection matches mood

---

## 6. Layer 3: Differentiation Features

> Prerequisites: Layer 2 features stable

---

### 3.1 Deep Research Mode

**What**: Multi-step autonomous web research with a dedicated LangGraph subgraph.

**Flow**: `plan_research → search_step → evaluate_coverage → (loop if insufficient) → synthesize → store_in_graph`

#### Implementation Steps

1. **New workflow**: `src/workflows/research_graph.py` -- dedicated `StateGraph` with research-specific state (query, plan, sources_found, coverage_score, synthesis)
2. **Nodes**: `plan_research` (LLM generates search plan), `search_step` (uses existing `web_search` + `web_extract`), `evaluate_coverage` (LLM assesses coverage 0-1.0), `synthesize` (produces structured Markdown with citations), `store_in_graph` (extracts entities into Neo4j)
3. **Integration**: Add `research_mode` to `AgentConfig.mode`, planner routes research-intent to the subgraph
4. **Output**: Generated note (via note sub-agent) + optional audio overview (Layer 2.2)
5. **Frontend**: Research progress view showing current step, sources found, coverage assessment

#### Verification

- [ ] Integration test: Submit research query → multiple search rounds → coverage reaches threshold → synthesis produced with citations
- [ ] Test: Research results stored as note with proper source attribution
- [ ] Test: Neo4j entities extracted from research synthesis

---

### 3.2 Vision-based Input

**What**: Accept images as input -- photos of math problems, screenshots of code errors, diagrams. LLM analyzes contextually.

#### Implementation Steps

1. **Backend**: Modify `src/routers/chat.py` to accept `multipart/form-data` with image files alongside text
2. **Storage**: Save images to `storage/images/{user_id}/{uuid}.{ext}`, reference via internal URL
3. **Message format**: Extend message schema to support `content: list[dict]` with `{"type": "text", "text": "..."}` and `{"type": "image_url", "image_url": {"url": "..."}}`
4. **Agent integration**: In `src/workflows/react_graph.py`, the agent node passes messages to the LLM. Vision-capable models (GPT-4o, Claude) handle image parts natively
5. **Frontend**: Add image upload button to `ChatInput.tsx` with:
   - Click-to-upload and drag-and-drop
   - Paste from clipboard (`Ctrl+V`)
   - Image preview before send
   - Multiple image support

#### Verification

- [ ] Test: Upload image → LLM receives image content → contextual response
- [ ] Test: Image stored persistently and referenced in message history
- [ ] Frontend test: Drag-and-drop, paste, click-to-upload all work

---

### 3.3 Calendar Integration

**What**: Google Calendar awareness for schedule-aware mission creation, focus time protection, optimal study window suggestions.

#### Implementation Steps

**Option A (via MCP -- preferred if Layer 2.1 done)**:
1. Connect to `@anthropic/google-calendar` MCP server
2. Tools appear automatically in planner
3. Zero backend code needed

**Option B (native)**:
1. Extend Google OAuth scope in `src/infrastructure/security/oauth.py` to include `calendar.readonly` and `calendar.events`
2. New module `src/infrastructure/integrations/google_calendar.py` with Google Calendar API client
3. New tools: `check_availability(date_range)`, `create_event(title, start, end)`, `get_upcoming_events(days)`
4. Register in tool registry
5. Frontend: Calendar overlay on existing `CalendarView.tsx` component

#### Verification

- [ ] Test: Ask "when am I free today?" → agent checks calendar → returns availability
- [ ] Test: "Schedule a study session for 2 hours this week" → creates event in free slot

---

### 3.4 Temporal Knowledge Graph

**What**: Bi-temporal fact tracking on Neo4j. Track when something was true (valid time) vs when Rio learned it (transaction time). Enables "What did we know about X last month?" queries.

#### Implementation Steps

1. **Extend Neo4j schema**: Add properties to all relationships:
   - `valid_from` (DateTime) -- when the fact became true
   - `valid_to` (DateTime, nullable) -- when the fact stopped being true
   - `recorded_at` (DateTime) -- when Rio learned this
   - `confidence` (Float, 0-1) -- Rio's confidence in this fact

2. **Modify**: `src/infrastructure/tools/neo4j_tool.py`
   - Update entity/relationship creation to include temporal properties
   - Add temporal Cypher queries: "facts valid at time T", "facts known at time T"
   - Contradiction detection: when a new fact contradicts an existing fact, set `valid_to` on the old fact and reduce its confidence

3. **New tool**: `search_temporal_graph(query, as_of_date)` -- search graph state as it was at a specific point in time

4. **Integration**: Register temporal search tool in tool registry

#### Verification

- [ ] Test: Create fact A at T1 → create contradicting fact B at T2 → query at T1 returns A → query at T2 returns B
- [ ] Test: Confidence scoring reduces for contradicted facts

---

### 3.5 Emotional Voice

**What**: TTS that adjusts intonation based on Rio's current emotional state.

#### Implementation Steps

1. **Extend**: `src/services/audio_service.py`
   - Before TTS synthesis, fetch emotional state via `EmotionalEngine.compute_emotional_context()`
   - Map mood → TTS parameters:

| Mood | Pitch | Speed | Volume | Pauses |
|------|-------|-------|--------|--------|
| happy | slightly higher | moderate | normal | normal |
| sad | lower | slower | softer | longer |
| tired | lower | slower | softer | longer |
| frustrated | normal | faster | normal | shorter |
| excited | slightly higher | faster | normal | shorter |
| neutral | normal | normal | normal | normal |

2. **Implementation**: For `edge-tts`, use `rate` and `pitch` parameters. For OpenAI TTS, use `speed` parameter and select voice variants. For future Qwen3 TTS, use speaker embeddings / style tokens.

3. **Frontend**: Show current mood indicator on audio player during playback

#### Verification

- [ ] Test: Generate audio with mood=happy → verify TTS parameters adjusted
- [ ] Test: Generate audio with mood=tired → verify slower speed, lower pitch
- [ ] A/B comparison: Same content, different moods → audibly different output

---

## 7. Layer 4: Advanced Platform

> Long-term investments. See existing `docs/plan_and_step.md` sections 25-32 for detailed specs.

### 4.1 Tiered Memory Architecture

**Build order** (from `docs/plan_and_step.md` section 25):
1. Formalize working memory in Redis (TTL strategy, key schema) -- 2-3 days
2. Split episodic/semantic collections in Qdrant with `source`, `timestamp`, `importance_score`, `access_count` metadata -- 5-7 days
3. Expand Neo4j from notes-only to all entities -- 3-5 days
4. Importance scoring with decay (nightly APScheduler job, uses automation infrastructure from Layer 1.3) -- 3-4 days
5. Curiosity-driven collection (background LangGraph node) -- 5-7 days

### 4.2 Self-Development Engine

**Build order** (from `docs/plan_and_step.md` section 26):
1. Constitution enforcement (values, boundaries)
2. Tool forge loop (identify capability gap → design tool → sandbox test → propose)
3. Sandbox evaluation environment
4. Proposal system (agent proposes new tools, user approves)

This is Rio's ultimate long-term differentiator. No competitor has an AI that can identify its own capability gaps and propose new tools.

### 4.3 Cross-Tool Integration via MCP

With MCP client support (Layer 2.1), adding integrations becomes configuration:

| Integration | MCP Server | Priority |
|-------------|-----------|----------|
| Google Drive | `@anthropic/google-drive` | 1st |
| Slack | `@anthropic/slack` | 2nd |
| Notion | `@anthropic/notion` | 3rd |
| Jira | `@anthropic/jira` | 4th |
| GitHub | `@anthropic/github` | 5th |

Each integration: install MCP server → add to registry → tools appear in planner automatically.

---

## 8. Architecture Patterns to Adopt

| Pattern | Source | Application in Rio | Priority |
|---------|--------|-------------------|----------|
| **Skills-as-directories** | OpenClaw | Modular capability packages with `SKILL.md` metadata files. Each skill is a directory with tool definitions, prompts, and config. | Layer 2 |
| **Bi-temporal fact tracking** | Graphiti | Extend Neo4j relationships with `valid_from`/`valid_to` timestamps. Enables temporal queries and contradiction detection. | Layer 3 |
| **Self-editing memory** | Letta/MemGPT | Agent can update/delete its own memory entries (not just append). Requires memory mutation tools. | Layer 4 |
| **Auto-model selection** | Notion AI | Route tasks to optimal model by complexity/cost. Simple questions → small model, complex reasoning → large model. | Layer 3 |
| **Source-grounding** | NotebookLM | When answering from user documents, answer ONLY from sources with citations. Reduces hallucination. | Layer 2 |

---

## 9. Protocols & Standards

| Protocol | Status | What It Does | Rio Action | Timeline |
|----------|--------|-------------|------------|----------|
| **MCP** (Model Context Protocol) | Industry standard, 97M+ monthly SDK downloads, 5,800+ servers | Standardized AI agent connections to tools/data ("USB-C for AI") | Implement client in Layer 2.1 | Layer 2 |
| **A2A** (Agent2Agent Protocol) | V0.3, Linux Foundation, 50+ partners | Agent-to-agent communication across frameworks | Monitor, implement when mature | Layer 4+ |
| **Graphiti** | Open source by Zep, 94.8% DMR benchmark | Temporally-aware knowledge graph with bi-temporal fact tracking | Adopt patterns in Layer 3.4 | Layer 3 |

---

## 10. Priority Matrix

| Feature | User Impact | Complexity | Dependencies | Layer | Est. Days |
|---------|------------|------------|--------------|-------|-----------|
| Contextual Note Resurfacing | High | Low | Layer 0 | 1 | 3-5 |
| Flashcards Phase 1 (SM-2) | **Critical** | Medium | Layer 0 | 1 | 8-12 |
| Scheduled Automations | High | Medium | Layer 0 | 1 | 5-8 |
| MCP Client | **Strategic** | Medium | Layer 0 | 2 | 10-14 |
| Audio Overview | High | Medium | Layer 0 | 2 | 8-12 |
| Adaptive Flashcards (Phase 2) | Medium | Low | L1.2 + Emotional Engine | 2 | 5-7 |
| Deep Research Mode | Medium | Medium | Layer 0 + Web Search | 3 | 10-14 |
| Vision Input | Medium | Low | Vision-capable LLM | 3 | 4-6 |
| Calendar Integration | Medium | Low-Med | L2.1 (MCP) or OAuth | 3 | 5-8 |
| Temporal Knowledge Graph | Medium | Medium | Neo4j enabled | 3 | 6-8 |
| Emotional Voice | Medium | Medium | L2.2 (Audio) + TTS | 3 | 4-6 |
| Tiered Memory | **Strategic** | High | Layer 0 | 4 | 18-26 |
| Self-Dev Engine | **Strategic** | Very High | Many | 4 | Months |

### Sequencing Recommendation

**Weeks 1-2** (parallel with Layer 0 tail):
- Design flashcard schema and SM-2 algorithm (pure logic, no system deps)
- Design automation model and cron evaluation (pure logic)

**Weeks 3-6** (Layer 1, once Layer 0 green):
- Ship Contextual Note Resurfacing (quick win, validates SSE pipeline)
- Ship Flashcards Phase 1 (new domain, parallel workstream)
- Ship Scheduled Automations foundation

**Weeks 7-12** (Layer 2):
- MCP Client (unlocks entire integration ecosystem)
- Audio Overview MVP (external TTS API)
- Adaptive Flashcards (extends Phase 1 with emotional engine)

**Weeks 13-18** (Layer 3):
- Vision Input (relatively simple)
- Deep Research Mode
- Calendar Integration (via MCP if available)
- Temporal Knowledge Graph

**Weeks 19+** (Layer 4):
- Tiered Memory Architecture
- Self-Development Engine
- Cross-tool integration expansion
