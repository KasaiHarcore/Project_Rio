# Rio — Replanned Dev Route

> **One rule above all: a layer must be stable and used daily before the next layer starts.**
> No new systems. No scope expansion mid-layer. Finish what's in front of you.

---

## What's Already Done (Keep, Don't Touch)

- RAG foundation — PyPDFLoader, chunking, Qdrant hybrid search, HyDE, reranking
- SQL worker — CRUD, read/write separation, Alembic, Pydantic schemas
- Web search — Tavily via WebSearchWorker
- LangGraph core — AgentState, graph.py, supervisor, checkpointer, Redis persistence
- Streaming — SSE via FastAPI, real-time chunk delivery
- HITL — SQL approval gate, node pause/resume
- Note worker — extraction, NoteEditor, KaTeX support
- Mission worker — auto-extraction, deadline tracking, Mission Board
- Memory — long-term PostgreSQL, short-term Redis, explicit MemoryWorker
- OS Control — PTY shell, browser via Playwright, GUI via pyautogui, risk tier system
- Auth — OAuth, JWT, user profiles
- Docker — containerized
- Arize Phoenix — tracing connected
- React frontend — chat shell, sidebar, streaming, artifact page, mission page

---

## Layer 0 — Stabilize What Exists

> **Goal: Rio runs without errors on a normal working session. No crashes, no broken flows.**
> Exit criterion: use Rio for one full work session (2+ hours) without hitting a bug.

- [ ] 0.1. Fix all broken or flaky worker routes
  - Map which workers currently fail or return garbage — RAG, SQL, Note, Mission, WebSearch
  - Fix supervisor routing so the right worker is called consistently
- [ ] 0.2. Fix streaming reliability
  - No dropped chunks, no silent failures mid-stream
  - Handle cut-off requests gracefully (item 18.3.1)
- [ ] 0.3. Fix memory TTL edge cases
  - Long conversation test for Redis short-term memory (item 6.3)
  - Validate message ordering (created_at ASC) under real load
- [ ] 0.4. Fix session memory across tabs
  - Agent stores session memory correctly — only exists in 1 chat session (item 18.4.8)
- [ ] 0.5. Write a basic smoke test suite
  - One test per worker: RAG, SQL, Note, Mission, WebSearch, Memory
  - Run on every code change before moving forward

---

## Layer 1 — Daily Driver Core

> **Goal: Rio replaces your daily workflow for learning and working as an AI Engineer.**
> Exit criterion: you open Rio first, not Claude.ai or your browser, for study and work sessions.

### 1A. Support Orchestrator (Simplified)

Replace the current keyword-based supervisor with intent-aware routing.
**Not the full 9-node graph yet** — just the minimum that makes Rio feel smart.

- [ ] 1A.1. Add support state to `AgentState`
  - `primary_goal: str | None`
  - `current_stage: Literal["explore", "understand", "plan", "execute", "review", "retain"] | None`
  - `current_friction: str | None`
  - `recommended_next_step: str | None`
- [ ] 1A.2. Add `assess_support_state` node
  - Infer goal and stage from conversation context
  - Keep it a single focused LLM call — not a chain
- [ ] 1A.3. Add `decide_intervention` node
  - Choose one intervention: teach / clarify / break_down / retrieve_evidence / draft_structure / recommend_next_step
  - Route to workers based on intervention, not keyword matching
- [ ] 1A.4. Emit 3 stream events only
  - `data-stage-assessment`
  - `data-intervention-decision`
  - `data-next-step`
- [ ] 1A.5. Render those 3 signals in the sidebar
  - "What Rio understands"
  - "What Rio thinks you need next"

### 1B. Notes — Make Them Actually Useful

- [ ] 1B.1. Auto-capture key insights mid-conversation (not just at session end)
- [ ] 1B.2. Surface relevant past notes at conversation start via RAG
- [ ] 1B.3. Export note to markdown file (Phase 1 from Note roadmap)
- [ ] 1B.4. Edit history view (Phase 1 from Note roadmap)

### 1C. Mission — Reliable Commitment Tracking

- [ ] 1C.1. Mission creation only triggers when user is clearly in execution stage
  - Not as default output of every conversation
- [ ] 1C.2. Session re-entry surfaces open missions automatically
  - "Last time you were working on X — still on it?"
- [ ] 1C.3. Fix deadline display on Mission Board

### 1D. Identity & Personality Foundation

- [ ] 1D.1. Create `config/constitution.md` — Rio's immutable identity rules
- [ ] 1D.2. Create `config/values.md` — transparency, partner, authorship, uncertainty rules
- [ ] 1D.3. Create `config/personality.md` — how Rio speaks (competence-first, direct, calm)
- [ ] 1D.4. Inject all three configs into system prompt at agent startup
- [ ] 1D.5. Tune response voice — less robotic, more like a sharp colleague

---

## Layer 2 — AI Engineer Power Tools

> **Goal: Rio becomes genuinely useful for coding, debugging, and deep technical work.**
> Exit criterion: Rio saves you real time in at least 3 different engineering tasks per week.

### 2A. Codebase RAG

- [ ] 2A.1. Project ingestion — index a local codebase into Qdrant
  - Read files, chunk by function/class, embed, store with file path + line metadata
- [ ] 2A.2. Code-aware retrieval — search across your own codebase
  - Ask "how does X work in my project" and get grounded answers
- [ ] 2A.3. Context-aware RAG — inject relevant code snippets into LLM context automatically

### 2B. OS Control — Stable and Safe

- [ ] 2B.1. PTY shell reliability pass — ensure state carries correctly across commands
- [ ] 2B.2. Risk tier enforcement — verify all tier 3+ actions require explicit approve
- [ ] 2B.3. Shell output summarization — LLM digests long terminal output into what matters
- [ ] 2B.4. Fix Playwright browser control — navigate + extract reliably

### 2C. Web IDE (Lightweight)

> Only if OS control is stable. Skip if it blocks other items.

- [ ] 2C.1. File tree view in sidebar — read project structure
- [ ] 2C.2. File open + read in chat context
- [ ] 2C.3. File edit with diff preview before applying

---

## Layer 3 — Memory & Continuity

> **Goal: Rio remembers who you are and what you're working on across sessions.**
> Exit criterion: starting a new session feels like resuming, not starting over.

### 3A. Temporal Continuity (Simplified)

- [ ] 3A.1. Track `last_interaction` and `time_gap` on session start
- [ ] 3A.2. Re-entry briefing based on gap size
  - Gap < 1h: no comment, continue
  - Gap 1–24h: "last time we were on X"
  - Gap 1–7 days: brief summary of open work
  - Gap > 7 days: fuller re-entry — what was happening, what needs attention
- [ ] 3A.3. Open thread tracker — list of unresolved problems Rio noticed
  - Surface on re-entry as context, not notifications

### 3B. Memory Architecture (Minimal Upgrade)

> Not the full 7-part #25 plan. Just what changes daily behavior.

- [ ] 3B.1. Episodic vs semantic split in Qdrant
  - `episodic`: things that happened
  - `semantic`: things that are true
- [ ] 3B.2. Importance scoring on memory writes
  - Simple formula: recency × access frequency × source weight
- [ ] 3B.3. Memory surfacing on session start — inject top-N relevant memories into context
- [ ] 3B.4. Graceful forgetting — beliefs not reinforced in 90 days → flagged, not deleted

---

## Layer 4 — Proactive Presence

> **Goal: Rio notices things and brings them to you — without being noisy.**
> Exit criterion: Rio surfaces something genuinely useful you didn't ask for, at least once per session.
> **Do not build this layer until Layer 3 is stable.**

- [ ] 4.1. Pending action cards in frontend
  - Every proactive action shown as a card: Action / Why / Impact / State
  - Controls: Approve / Deny / Discuss / Edit
- [ ] 4.2. Authority model enforcement
  - `talk` — no writes
  - `draft` — Rio proposes, doesn't act
  - `act` — Rio creates reversible structure
  - `confirm` — must ask before destructive actions
- [ ] 4.3. `reflect_outcome` node — after intervention, check: did this help?
- [ ] 4.4. `commit_support_state` — persist goal continuity and revisit-later signals across turns
- [ ] 4.5. "Things Rio wants to revisit later" surface in sidebar
- [ ] 4.6. Interruption budget — Rio self-limits proactive initiations per session

---

## Layer 5 — Belief, Relationship & Situational Awareness

> **Goal: Rio knows you well enough to adapt without being told.**
> **Do not build this layer until Layer 4 is stable and trusted.**

- [ ] 5.1. `UserBelief` model — structured facts about you with confidence scores
- [ ] 5.2. `RelationshipModel` — communication style, shared history, collaboration rhythm
- [ ] 5.3. Belief-confidence injection into responses
  - High confidence (>0.85): stated directly
  - Medium (0.5–0.85): hedged
  - Low (<0.5): held internally, not stated
- [ ] 5.4. Cognitive state inference (focused / exploring / tired / blocked / in-flow)
- [ ] 5.5. Behavior adaptation based on inferred mode
- [ ] 5.6. Predictive intent — pre-fetch relevant context before you ask

---

## Permanently Deferred (Someday / Never)

> These are not cut. They're parked. Revisit after Layer 3 is complete.

- Self-development engine (26) — Rio writes its own tools
- FastMCP Tool Gateway (24) — premature abstraction at current scale
- Microservice migration (27) — trigger: after all layers above are stable
- Mobile app (28) — after web is solid
- ColPali multimodal retrieval (25.6) — not needed for daily workflow yet
- Curiosity-driven memory collection (25.5) — risk of knowledge base pollution
- Weekly reflection / APScheduler (26.4) — too much infrastructure for current value
- AWS deployment (18.2) — local first, cloud later
- XP / Progression system (21.6) — revisit if relevant after core is working

---

## Testing Rule (Non-Negotiable)

> Every item shipped must have at least one test before moving to the next item.
> No exceptions. A feature without a test is not done.

- Unit test per worker and per service
- Integration test per layer before declaring that layer complete
- Smoke test suite runs before any new layer begins

---

## Current Priority

```
NOW:    Layer 0 — Stabilize
NEXT:   Layer 1A — Support Orchestrator (simplified)
THEN:   Layer 1B + 1C + 1D in parallel
HOLD:   Everything else
```

---

## What Rio Is

Rio is a sharp, persistent AI colleague that helps you study, learn, and build — as an AI Engineer.

It is not a JARVIS. It is not a platform. It is not a framework.

It is a tool that works well every day, knows your context, and makes you faster.

Build that first. The rest follows naturally.