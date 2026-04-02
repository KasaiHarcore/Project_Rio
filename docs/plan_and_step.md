# Rio System — Dev Route (AGILE - Monolithic → Microservice)

---

## Completed Baseline

1. Establish RAG Basic Foundation (**DONE**)
   - `PyPDFLoader` text extraction in `src/infrastructure/rag/ingestion.py`
   - `RetrievalWorker` (`src/workflows/workers/retrieval_worker.py`) inside LangGraph
2. Integrate Streamlit (**DONE**)
3. Complete Basic RAG System Based on PDF Extraction (**DONE**)
   - Extracted text is split into chunks and embedded via `src/infrastructure/llm/` models
   - Vectors stored in Qdrant Db and queried through local hybrid search
4. Develop Advanced RAG Features (**DONE**)
   - 4.1. Add SQL Database - PostgreSQL via SQLAlchemy (**DONE**)
     - Tables via SQLAlchemy defined in `src/models/` (e.g., `user_profile.py`, `note.py`)
   - 4.2. Implement CRUD Operations with Full Case Handling (**DONE**)
   - 4.3. Add Read/Retrieve Operations (**DONE**)
   - 4.4. Integrate Alembic (**DONE**)
     - Managed in root `alembic/` folder and `alembic.ini`
   - 4.5. Resolve Connection Issues (**DONE**)
   - 4.6. Format Input/Output with Pydantic (**DONE**)
     - Handled via schema validation locally in `src/schemas/`
   - 4.7. Implement SQL Chat mode (**DONE**)
     - 4.7.1. Schema transferring to LLM - Table name only - DBCopilot (**DONE**)
       - Controlled by `sql_schema_service.py` to inject concise schema into prompt
     - 4.7.2. READ - WRITE separation (**DONE**)
       - Built into `SQLWorker` (`src/workflows/workers/sql_worker.py`)
5. Integrate Qdrant Vector Store (**DONE**)
   - Setup in `get_vector_db_tool()` (`src/infrastructure/tools/qdrant_tool.py`) handling autocreation
   - 5.1. Create HyDE and Query Rewriting (**DONE**)
   - 5.2. Add Sparse Embeddings and Hybrid Search (**DONE**)
     - Implemented natively for semantic + keyword (BM25) matching logic
   - 5.3. Add Cohere Reranker (**DONE**)
   - 5.4. Image Understanding → Text extraction → store same as other docs (In Progress)
     - PDF OCR uses `ExternalOCRClient` in `ingestion.py`
   - 5.5. Implement Web Search with Tavily (**DONE**)
     - Handled by `WebSearchWorker` (`src/workflows/workers/web_search_worker.py`)
6. Add Chat History Management
   - 6.1. Long-term memory - PostgreSQL (**DONE**)
     - Tracked by `ChatHistoryService` (`src/services/chat_history_service.py`) in `chat_messages` table
   - 6.2. Short-term memory - Redis (**DONE**)
     - Hosts LangGraph active states and thread logic
   - 6.3. Control memory TTL (Simple test pass — needs long conversation test)
   - 6.4. Re-order requests from system to database (**DONE**)
     - State loaded correctly sorted by `created_at` ASC
   - 6.5. Episodic + Semantic + Graph Memory support (→ see 25)
   - 6.6. Update retrieval method (→ see 25.2)
7. Update UI (Continuous improvement)
8. Form Input/Output Storing Structure in Markdown Format for Qdrant (**DONE**)
9. Convert LangChain to LangGraph (**DONE**)
   - Built around the single overarching `AgentState` in `src/workflows/state.py`
   - 9.1. Implement State Management (**DONE**)
   - 9.2. Add Configuration - Threading (**DONE**)
   - 9.3. Initialize Persistence and Checkpointer (**DONE**)
     - Configured inside `Checkpointer` (`src/workflows/checkpointer.py`)
11. Durable Execution Engine and Structure (**DONE**)
    - `graph.py` maps the `Supervisor` node to all subsystem workers
    - 11.1. Apply `durability="sync"` in graph stream (**DONE**)
12. Evaluation
    - 12.1. Integrate LangSmith for Tracing (**DONE**)
    - 12.2. Integrate RAGAS for Evaluation (**DONE**)
13. Add Human-in-the-Loop (HITL)
    - Node pauses in graph are used for safety checks (ex: `sql_worker.py` yielding for mutations)
    - `sql_approval.py` (`POST /api/sql-approve`) resumes state execution
    - 13.1. Allow / Not allow tool call request like Copilot on SQL (**DONE**)
      - 13.1.1. Enable editing of tool call request and apply on SQL (**DONE**)
      - 13.1.2. Planning Step — affects LLM action (**DONE**)
      - 13.1.3. Reflection + Verify → Return Information → Finalize (**DONE**)
14. Add Streaming Responses (**DONE**)
15. Add Caching with Redis (**DONE**)
16. Add Neo4j beside Qdrant for extracting information (**DONE**)
    - `neo4j_tool.py` manages graph nodes/relationships logic (extracted via LLM)
    - `graph_rag.py` executes parallel cypher queries merged with vector DB queries
17. Explore Multi-Agent System (**DONE**)

---

## Deployment & UI

18. Deployment
    - 18.1. Dockerize the Application (**DONE**)
    - 18.2. Deploy on Cloud
      - 18.2.1. AWS: BedRock, EC2, S3, DynamoDB, Neptune, ECS, EKS, IAM
      - **Deferred** — design service boundaries locally first, migrate after all core systems complete
    - 18.3. Implement REST API Endpoints - FastAPI (**DONE**)
      - All routers sit under `src/routers/` explicitly separated by features (e.g., `chat.py`, `settings.py`)
      - 18.3.1. Handle cut-off request (Need test)
    - 18.4. New UI with React
      - Frontend strictly relies on `/api/chat/stream` for generating dynamic responses
      - 18.4.0. Test all MVP workers — RAG, SQL, Web Search (**DONE**)
      - 18.4.1. Fix Note worker — re-mapping quicknote instead of raw output (**DONE**)
        - Implemented `NoteEditor.tsx` with Markdown and KaTeX math support mapped to `NoteWorker` outputs
      - 18.4.2. Fix Workspace — cannot add file (**DONE**)
      - 18.4.3. Test Planning worker (**DONE**)
      - 18.4.5. Agent response line by line — mimic human response; sticker support (**DONE**)
        - Driven by `MOOD_STICKERS` and `SmartDataCard.tsx` reacting to stream chunks character by character
      - 18.4.6. Complete Artifact Page → map workspace at Operation page (**DONE**)
      - 18.4.7. Map Mission page → Upcoming Deadline at Office page (**DONE**)
      - 18.4.8. Agent stores Session memory — only exists in 1 chat session
      - 18.4.9. Fix agent name in chat (**DONE**)
      - 18.4.10. Support IDE on web — mimic vscode.dev or Replit (If possible)
      - 18.4.11. Re-make autonomous coding agent (Copilot-style)
        - 18.4.12. Project Ingestion
          - List all projects in workspace
          - Read a subset of files, chunk, summarize
        - 18.4.13. Planning
          - Generate TODO list
          - Allow user to review / modify manually or auto
          - Engineering controls over AI behavior
        - 18.4.14. Execution
          - Checklist per task
          - Complete each task: Create → Test → Verify
          - Allow user interrupt mid-task
          - Summarize what happened and result

---

## AI-First Product Priority Order (NEW)

> **Priority: critical — this is the build order for Rio as an AI-first supportive agent for studying, learning, and working.**

Rio is not a mission app with AI features.
Rio is not a generic chatbot with many tools.

Rio is the product.

`Mission`, `Note`, `RAG`, `SQL`, `WebSearch`, `Memory`, and `OSControl` are support systems under Rio.

Build priority should follow this order:

1. **Identity, values, and personality foundation**
   - Build 29 first
   - Rio needs stable decision rules before becoming more proactive
2. **Support orchestrator above the current supervisor**
   - Replace worker-first routing with intervention-first reasoning
   - Rio should ask "what does the user need next?" before deciding which worker to use
3. **Frontend control surface for proactive behavior**
   - Before Rio becomes more aggressive, the user must be able to see, understand, and control proposed actions
4. **Temporal continuity**
   - Re-entry, open threads, time-gap awareness
5. **Belief and relationship model**
   - Personalization and collaboration calibration
6. **Initiation and proactive presence**
   - Rio reaches out only after the behavior core and user-control surfaces are stable
7. **Situational awareness**
   - World model, predictive context, behavior adaptation

**Rule:**
- Do not build stronger proactive behavior before identity, values, support orchestration, and user-facing control are stable.

---

## Frontend Control & Agent Visibility (NEW)

> **Priority: high — must exist before Rio acts more aggressively.**

If Rio is proactive, the frontend cannot feel like hidden automation.

The user should always be able to:

- see what Rio noticed
- see what Rio wants to do
- see why Rio wants to do it
- approve, deny, discuss, or modify it
- review what already happened

### Main support surface

- `What Rio understands`
  - short summary of current goal / situation
- `What Rio thinks you need next`
  - one recommended next step
- `What Rio wants to do`
  - pending suggested or auto-draft actions
- `Recent actions`
  - what Rio already created, changed, or updated

### Pending action card design

Every proactive action should be surfaced as a card with:

- `Action`
- `Why`
- `Impact`
- `State`

Controls:

- `Approve`
- `Deny`
- `Discuss`
- `Edit`

### Action states

- `Observed`
- `Suggested`
- `Waiting for you`
- `Running`
- `Done`
- `Dismissed`

### Action authority / initiative modes

- `Suggestion only`
- `Auto-draft`
- `Auto-act`
- `Approval required`

### Discussion flow

`Discuss` should not cancel the action by default.

It should convert the action into collaborative conversation, for example:

- "Don't create it yet"
- "Make it narrower"
- "Use a note instead"
- "Wait until tomorrow"

### Product-language rule

Avoid vague or overly internal labels in the UI.

Use:

- `What Rio thinks is getting in the way`
  - instead of `blocker diagnosis`
- `Things Rio wants to revisit later`
  - instead of `follow-up markers`

The main UI should feel like a supportive agent interface, not a workflow debugger.

---

## Support Orchestrator Implementation

> **Priority: critical — this is the concrete engineering bridge between the AI-first product idea and the current supervisor-worker codebase.**

- 18.A. Replace worker-first supervision with support-first orchestration
  - Add support-layer state to `AgentState`
    - `primary_goal`
    - `goal_candidates`
    - `current_stage`
    - `current_friction`
    - `secondary_frictions`
    - `knowledge_gap`
    - `execution_risk`
    - `initiative_level`
    - `confidence_to_act`
    - `recommended_next_step`
    - `revisit_later`
    - `support_summary`
  - Add intervention state
    - `current_intervention`
    - `intervention_reasoning`

- 18.B. Add new orchestration nodes to the LangGraph workflow
  - `observe_context`
  - `assess_support_state`
  - `decide_intervention`
  - `reflect_outcome`
  - `commit_support_state`
  - Keep existing workers intact at first — Mission, Note, RAG, SQL, WebSearch, Memory, OSControl remain capability subsystems

- 18.C. Intervention-first behavior model
  - Rio chooses intervention before choosing a worker
  - Supported interventions:
    - `teach`
    - `clarify`
    - `challenge`
    - `break_down`
    - `plan`
    - `retrieve_evidence`
    - `draft_structure`
    - `commit_structure`
    - `review_progress`
    - `summarize_learning`
    - `recommend_next_step`

- 18.D. Stream contract upgrades for AI-first support behavior
  - Add stream events:
    - `data-support-assessment`
    - `data-stage-assessment`
    - `data-intervention-decision`
    - `data-next-step`
    - `data-draft-mission`
    - `data-draft-note`
    - `data-revisit-later`
    - `data-pending-action`
  - Preserve existing worker and supervisor events for compatibility

- 18.E. Frontend store and shell integration
  - Extend chat/sidebar store with:
    - current stage
    - current friction
    - intervention
    - next step
    - revisit-later items
    - pending actions
    - recent actions
  - Render support state inside the main agent shell
  - Keep thread continuity and current streaming model intact

- 18.F. Pending action interaction model
  - Every proactive action must surface:
    - `Action`
    - `Why`
    - `Impact`
    - `State`
  - Every proactive action must support:
    - `Approve`
    - `Deny`
    - `Discuss`
    - `Edit`

- 18.G. Implementation order
  - Phase 1:
    - add support state fields
    - add `assess_support_state`
    - add `decide_intervention`
    - emit support-state stream events
  - Phase 2:
    - refactor supervisor into support orchestrator
    - route by user stage and friction, not worker keywords alone
  - Phase 3:
    - add draft vs commit behavior for Mission and Note
  - Phase 4:
    - render pending action cards and support panels in frontend
  - Phase 5:
    - connect proactive initiation and situational awareness on top of the stable support layer

---

## Testing, Documentation

19. Testing & Optimization
    - 19.1. Unit Testing (TDD) — **do not defer; build alongside each new system**
      - Core loop test suite first: planning → worker routing → retrieval → response
      - Each new service in 29–31 must ship with tests before moving to the next
    - 19.2. Performance Optimization
20. Documentation & Tutorials — README
    - 20.1. User Guide
    - 20.2. Developer Guide
    - 20.3. API Reference (with proper usage)

---

## Additional Backend Core Systems (**In Progress / Planned**)

### 21. Completed Core Systems

- 21.1. Note Management & Auto-Extraction
  - `NoteWorker` (LangGraph), `NoteService`, `Note` Models
  - Analyzes conversation history to extract actionable insights
  - Generates JSON-structured session-scoped sticky notes with optional TODO lists, persists to DB
  - Support Audio, Video, Transcript, etc.

  - **Note Feature Roadmap (Editor / UX) — linear scaling (Planned)**
    - Phase 1 — Foundation (single-note, safe defaults)
      - Export / Import Note in full markdown format
      - Edit history view
    - Phase 2 — Structure & Navigation (multi-note workflows)
      - Drag and Drop layout to separate content like a table on one page
      - Support breadcrumbs (Note link to another Note in app)
    - Phase 3 — Rich Content & Presentation (expressiveness)
      - Support diagram rendering (Mermaid, SVG, etc.)
      - Support image, video, slide, etc. input
      - Personalize Note design (cover image, comment, text font, text color, etc.)

- 21.2. Mission & Goal Tracking System
  - `MissionWorker` (LangGraph), `MissionService`, `Mission` Models
  - Auto-extracts long-term trackable tasks, estimates time, sets deadlines, groups by category
  - Persistent tasks populate Mission Board across sessions
  - Mission is a subsystem for commitment tracking, not the center of the product
  - Rio should create missions when execution structure is genuinely useful, not as the default output of every conversation

- 21.3. Emotional & Persona Engine — "Living AI"
  - `EmotionalEngine`, `EmotionalState`, `RelationshipEvent` Models, LLM Sentiment Analyzer
  - State machine tracking mood, affinity, interaction streaks, energy decay/recovery based on time gaps
  - Time-of-day modifiers, headpat interactions, forced tired states on low energy
  - Dynamic persona prompt injection based on relationship tiers: Stranger → Bonded
  - Persona must remain competence-first:
    - observant
    - supportive
    - direct
    - calm under ambiguity
    - willing to challenge once when needed
  - Relationship flavor should never overpower practical value, clarity, or judgment

- 21.4. Workflow Planning & Execution Engine
  - `PlanningWorker`, LangGraph Executor (`run_workflow`, `stream_workflow`)
  - Planning step assesses complexity, selects workers (SQL, RAG, WEB_SEARCH), charts logic path
  - Durable PostgreSQL checkpointing, multi-worker streaming, HITL interruptions (e.g. SQL approval)

- 21.5. LLM Guardrails & Safety (**DONE**)
  - `InputGuardrail`, `OutputGuardrail` (LangGraph nodes)
  - Deterministic limits (character length) + LLM-based categorization
  - Blocks prompt injections, off-topic prompts, unsafe content

- 21.6. Dashboard & XP / Progression Tracking
  - `XPService`, `DashboardService`
  - Global analytics, recent chat metrics, mission deadlines, XP progression mechanics

- 21.7. Real-time Communication — WebSockets (**DONE**)
  - Async delivery of LangGraph agent events and UI state updates in real-time

- 21.8. Identity & User Management
  - OAuth integrations, JWT + JWK, `AuthService`, User Profiles & Settings

- 21.9. Explicit Memory Management (**DONE**)
  - `MemoryWorker`, `MemoryAction` logic (STORE, RECALL, FORGET)
  - Parses and semantic-matches intents for explicit facts control ("Remember that", "Recall", "Forget")
  - Directly interfaces with `memory_store` to handle UUID-backed user facts

- 21.10. Note Collection System
  - `CollectionService`, `NoteCollection` Models, `collection.py` Router
  - Provides folder-like hierarchical organization for grouping related notes, complete with global note counting capabilities

- 21.11. Artifact & File Management System
  - `ArtifactService`, `Artifact` Models, `artifact.py` Router
  - Handles CRUD, parent-child version history, and auto-deletion (CASCADE) for AI-generated artifacts mapped to conversation threads

- 21.12. User Settings, Onboarding & Profile Engine (**DONE**)
  - `SettingsService`, `UserSettings`/`UserProfile` Models, `settings.py` / `onboarding.py` Routers
  - Manages global configs, LLM preferences, onboarding workflow, and secure encrypted external API key storage

- 21.13. Admin Operations & Reset Tools
  - `AdminService`, `admin.py` Router
  - System orchestration handlers for full SQL database drops, vector data recreation, and orphaned Enum cleanup

---

### 22. SVG Diagram Rendering

- 22.1. Backend: LLM generates raw SVG string on diagram-type requests (**DONE**)
- 22.2. Frontend: render SVG inside a sandboxed iframe or `dangerouslySetInnerHTML` in React (**DONE**)
- 22.3. Design system CSS injected into iframe at load — nine color ramps, text classes, node hover, arrow marker (**DONE**)
- 22.4. `onclick` nodes mapped to `sendMessage()` callback (**DONE**)
- 22.5. Dark mode: CSS variables auto-adapt, no hardcoded hex (**DONE**)
- 22.6. SVG prompt guide stored as system context (**DONE**)
- 22.7. Diagram types supported (**DONE**)

---

### 23. OS Control Layer — PTY + Execution Surface

- 23.1. PTY shell via `pexpect` (**DONE**)
  - Persistent bash session — state carries across commands (`cd`, `export`, `conda activate`) (**DONE**)
  - Stdout/stderr streamed back as real-time context for next LLM call (**DONE**)
  - Interactive programs (vim, ssh, conda) work because PTY mimics real terminal
  - Session managed as singleton per user session (**DONE**)
  - Implemented via `PTYSession` + `PTYSessionManager` in `src/infrastructure/os_control/pty_session.py`
  - Cross-platform: subprocess on Windows, pexpect-compatible on Linux/macOS
- 23.2. Browser control via Playwright (**DONE**)
  - `navigate`, `click`, `extract_text`, `screenshot` actions (**DONE**)
  - Tier 3 for read operations, tier 4 for form submission and clicks (**DONE**)
  - Implemented via `BrowserController` in `src/infrastructure/os_control/browser_controller.py`
- 23.3. GUI control via `pyautogui` (**DONE**)
  - `click`, `type`, `screenshot`, `find_element` actions (**DONE**)
  - Tier 4 — requires explicit approve (**DONE**)
  - Implemented via `GUIController` in `src/infrastructure/os_control/gui_controller.py`
- 23.4. Passive screen vision
  - Periodic screenshot + OCR diff
  - Importance classifier before anything stored
  - Relevant context written to Redis working memory with short TTL
- 23.5. Voice output as execution surface
  - **Qwen3 TTS** — fully local, default, 1.6B params, runs on GPU
  - Async speech queue via `asyncio.Queue` — interruptible mid-sentence
  - Sentence-boundary chunking for low-latency streaming TTS
  - Global hotkey wires to `sd.stop()` to interrupt speech immediately
- 23.6. Risk tier system — approval gate fires automatically based on declared tier (**DONE**)

  | Tier | Examples | Gate |
  |------|----------|------|
  | 1 | web search, RAG read, notes read | none |
  | 2 | notes write, SQL SELECT | soft confirm |
  | 3 | SQL mutate, file write | hard confirm |
  | 4 | shell exec, browser click, GUI control | explicit approve |
  | 5 | destructive ops — rm, format, overwrite | type to confirm |

**Notes:**
- All OS tools declare `risk_tier` in Pydantic metadata — gate fires without Rio reasoning about it per call (**DONE**)
- All PTY output, approval events, GUI actions logged via `log.py` (**DONE**)
- `Constructs`: `OSControlWorker`, `PTYSession`, `BrowserController`, `GUIController`, `VoiceOutputService`
- New constructs implemented: `OSControlService`, `PTYSessionManager`, `ApprovalRequest`/`ApprovalResponse`
- Router: `src/routers/os_control.py` — POST /os/shell, /os/shell/classify, /os/browser, /os/gui
- LangGraph worker: `src/workflows/workers/os_control_worker.py` — integrated into supervisor graph

---

### 24. FastMCP Tool Gateway

- 24.1. FastMCP gateway — single FastAPI endpoint proxying all MCP tool servers
  - Auth, rate limiting, audit logging at gateway level
  - Hot-reload: new tool servers register without gateway restart via `gateway.reload()`
- 24.2. Convert existing tools to FastMCP servers — each a standalone Python file in `tools/`
  - `mcp_web_search` — wraps Tavily (tier 1)
  - `mcp_qdrant_query` — read from Qdrant (tier 1)
  - `mcp_sql_read` — SELECT only (tier 1)
  - `mcp_sql_write` — mutate with approval (tier 3)
  - `mcp_note_read` — read and traverse note graph (tier 1)
  - `mcp_note_write` — create/update note in Neo4j + Qdrant (tier 2)
  - `mcp_os_shell` — PTY shell execution (tier 4)
  - `mcp_browser` — Playwright browser control (tier 3–4)
  - `mcp_gui` — pyautogui desktop control (tier 4)
  - `mcp_speak` — Qwen3 TTS voice output (tier 1)
- 24.3. Approval gate via Redis pub/sub → frontend confirm dialog
  - Approval state stored with TTL — expired approvals auto-reject
  - Reuses existing Redis infrastructure
- 24.4. Tool registry in PostgreSQL — name, version, path, risk_tier, approved_by, approved_at, active

**Architecture rule:**
Workers are LangGraph agent nodes — they reason, loop, multi-step. MCP servers are deterministic single-purpose tools. Workers call MCP tools through the gateway. Workers are never converted into MCP servers.

**Notes:**
- `Constructs`: `MCPGateway`, `ToolRegistry`, `ApprovalGate`, per-tool `FastMCP` instances
- Pydantic for all tool inputs, outputs, metadata
- Follow existing modular OOP structure, docstrings, typing throughout

---

### 25. Memory Architecture Upgrade

- 25.1. Three-tier memory model
  - **Tier 1 — Working memory** (Redis, TTL 24–72h): recent context, active drafts, session state, web search cache — formalize TTL strategy and key schema
  - **Tier 2 — Long-term memory** (Qdrant, two named collections):
    - `episodic`: things that *happened* — conversations, actions, timestamped events
    - `semantic`: things that are *true* — facts, concepts, summaries from docs and web
    - Every chunk carries: `source`, `timestamp`, `importance_score`, `access_count`, `type`
    - `source` enum: `user` / `agent_initiated` / `document` / `screen`
  - **Tier 3 — Graph memory** (Neo4j): extend from notes-only to all entities Rio encounters; on document ingest extract named entities → upsert into Neo4j

- 25.2. Hybrid retrieval pipeline upgrade
  - BM25 sparse (Qdrant) + dense vector (Qdrant) + Neo4j graph traversal (1–2 hops)
  - Cohere reranker scores all candidates together before context assembly
  - Cypher traversal:
```cypher
    MATCH (n)-[r*1..2]-(related)
    WHERE n.name IN $entity_names
    RETURN related.content, type(r), related.name
    LIMIT 20
```

- 25.3. Integrate `mem0` on top of Qdrant
  - Manages episodic/semantic split, deduplication, retrieval ranking
  - Drop-in addition to existing Qdrant setup

- 25.4. Importance scoring and memory decay
  - Score formula: `importance_score = recency_weight × access_frequency × source_weight`
  - Source weights: `user` > `document` > `screen` > `agent_initiated`
  - Nightly APScheduler consolidation pass:
    - Promote frequently accessed working memory → long-term semantic store
    - Expire low-score items not accessed in 30 days
    - Compress episodic items older than 90 days into summaries

- 25.5. Curiosity-driven memory collection
  - Background LangGraph node — runs on schedule or low-activity trigger
  - Picks topic with shallow coverage from recent conversations → Tavily search → summarize → write to Qdrant with `source: agent_initiated`
  - Rio builds its own knowledge base over time independent of explicit user queries

- 25.6. ColPali multimodal retrieval
  - For documents containing images, diagrams, charts, scanned pages
  - Embeds pages as images rather than extracted text — replaces OCR-only path from 5.4 for visual-heavy docs
  - Separate `multimodal` Qdrant collection alongside existing text collection

- 25.7. Graceful forgetting system
  - `BeliefStore` tracks every learned fact about the user with confidence score and contradiction count
  - When contradictions exceed threshold → flag belief for review, reduce confidence, do not silently retain
  - Annual consolidation pass: beliefs not reinforced in 365 days → archived, not deleted (recoverable)
  - Rio never treats old beliefs as current facts without recency validation
  - `Constructs`: `BeliefStore`, `BeliefValidator`, `ForgettingScheduler`

**Notes:**
- `Constructs`: `MemoryService`, `IngestionPipeline`, `ImportanceScorer`, `ConsolidationScheduler`, `CuriosityCollector`
- All memory writes go through ingestion pipeline: chunk → embed → score → route to tier
- `source` field is mandatory on every memory write — use enum, not freeform string
- Pydantic models for all memory chunk schemas

---

### 26. Self-Development Engine

- 26.1. Self-dev as a dedicated mode alongside `chat`, `web_search`, `rag`, `sql`, `os_control`
  - Mode entry swaps three things automatically:
    1. System prompt: constitution prepended
    2. Tool surface: only forge tools available — production tools inaccessible
    3. Audit log: all actions written to separate `self_dev_audit` table
  - `self_dev_enabled: bool` in config — global kill switch, disable without touching other modes
  - LangGraph routing:
```python
    def route_mode(state: RioState) -> str:
        if state["mode"] == "self_dev":
            return "forge_subgraph"
        return "normal_supervisor"
```

- 26.2. The Constitution (`config/constitution.md` — version controlled, Rio cannot modify)
  - **Identity rules**: personality, voice, and Rio character are immutable; Rio cannot propose changes to constitution or core personality prompt
  - **Hard technical rules**:
    - Network tools must route through `mcp_web_search` wrapper
    - File-mutating tools must append to audit log
    - Tier 3+ tools must declare `risk_tier` in Pydantic metadata
    - No tool may modify another tool's source directly — proposals only
    - All generated code must include ≥ 3 test cases before sandbox execution
  - **Proposal quality checklist** (Rio self-evaluates before sandbox):
    - Does this tool already exist in the registry?
    - Is scope minimal and single-purpose?
    - Does it have ≥ 3 test cases?
    - Does it declare a risk tier?
    - Does it pass all hard technical rules?

- 26.3. Tool forge loop (LangGraph subgraph — own state schema, isolated from normal agent state)
```
  detect_gap
      → write_spec           (Pydantic-validated: name, inputs, outputs, risk_tier, test cases)
      → generate_code        (complete FastMCP server file)
      → constitution_check   (LLM call → pass/fail + reasoning; fail = early exit, no sandbox cost)
      → sandbox_eval         (Docker or e2b: no host FS, network allowlist, 30s timeout)
          → fail: back to generate_code (max 3 retries then abort)
          → pass: proposer   (diff view + plain description + risk tier → user approve/reject)
```

- 26.4. Forge loop trigger sources
  - Rio detects a capability gap during normal operation
  - Explicit user request
  - Curiosity collector surfaces a gap
  - **Weekly reflection trigger**: APScheduler fires Sunday night
    - Reflection prompt: *"Review the last 7 days. What tasks required multiple attempts? What did you lack a tool for? What could be more efficient? Produce a structured improvement proposal."*
    - Proposal surfaced Monday morning for review

- 26.5. Tool versioning and hot-loading
  - Every approved tool: version tag + rollback pointer
  - Tool registry in PostgreSQL: name, version, path, risk_tier, approved_by, approved_at, active
  - `gateway.register("tools/new_tool.py")` — hot-load without restart
  - `gateway.rollback("tool-name")` — one-command rollback

- 26.6. Full self-dev cycle:
  - Agent finds gap
  - Research online / construct baseline approach workflow
  - Draft tool spec
  - Test on Docker sandbox
  - Evaluation and optimization
  - Propose to user
  - Merge into codebase (frontend + backend integration)

**Notes:**
- `Constructs`: `SelfDevMode`, `ConstitutionLoader`, `ForgeSubgraph`, `ToolForge`, `SandboxRunner`, `ProposalService`, `ReflectionScheduler`
- Forge subgraph has its own LangGraph `ForgeState` — does not share state with normal `RioState`
- All forge events logged via `log.py`
- Pydantic for all forge schemas: `ToolSpec`, `ForgeResult`, `ConstitutionCheckResult`, `ProposalPayload`
- Generated tool files follow same code standards as rest of codebase: docstrings, typing, error handling, `log.py`

---

### 27. Microservice Migration

> **Trigger**: after local monolith baseline is stable and all core systems are tested.

- 27.1. Design service boundaries while still monolithic — identify seams now
  - `memory-service` — Qdrant + Neo4j + Redis memory ops
  - `tool-gateway-service` — FastMCP gateway + tool registry
  - `agent-service` — LangGraph supervisor + workers
  - `forge-service` — self-dev engine (isolated by design from 26.x)
  - `user-service` — auth, profiles, XP
  - `mission-service` — mission tracking
  - `media-service` — voice output, screen capture, file storage
- 27.2. Dockerize each service boundary
- 27.3. AWS target stack:
  - ECS / EKS — container orchestration
  - RDS — PostgreSQL managed
  - S3 — document, audio, artifact storage
  - DynamoDB — high-throughput session/cache layer
  - Neptune — managed graph DB (if migrating off self-hosted Neo4j)
  - Bedrock or EC2 GPU — LLM inference
  - IAM — service-level access control

---

### 28. Mobile Connection

- 28.1. FastAPI REST endpoints already planned (18.3) — mobile consumes same API
- 28.2. WebSocket support already in place (21.7) — real-time events work on mobile
- 28.3. React Native or PWA wrapper around existing React frontend
- 28.4. Voice input/output on mobile — native mic API + TTS endpoint
- 28.5. Push notifications for mission deadlines, Rio-initiated proposals, weekly reflection results

---

### 29. Identity & Values System (NEW)

> **Priority: high — build before 30 and 31. These configs govern all Rio behavior, not just the forge.**

- 29.1. Core config files — version controlled, Rio cannot modify any of these directly
  - `config/constitution.md` — who Rio is (identity, immutable character rules)
  - `config/values.md` — how Rio makes decisions across all modes, not just self-dev
    - Transparency rule: Rio always surfaces what it knows, its confidence level, and where it may be wrong
    - Partner rule: Rio is allowed and expected to disagree — once, clearly, without being preachy
    - Authorship rule: Rio supports the user's own thinking, never replaces it
    - Uncertainty rule: Rio never presents a low-confidence belief as a fact
  - `config/personality.md` — how Rio expresses itself (evolvable over time with user approval)
  - `config/relationship.md` — who the user is to Rio (grows continuously, written by Rio, reviewed by user)

- 29.2. `ConstitutionLoader` extended to load all four configs at agent startup
  - Injected into system prompt layer before any worker runs
  - Values config governs all decision nodes — not scoped to forge only
  - `Constructs`: `IdentityConfig`, `ValuesConfig`, `PersonalityConfig`, `RelationshipConfig`

- 29.3. Values enforcement node in LangGraph
  - Lightweight check node inserted between planning and execution
  - Not a guardrail (that already exists in 21.5) — this is a judgment layer
  - Asks: does the planned action align with values? If uncertain → surface to user before proceeding
  - Logged via `log.py` whenever values check fires
  - Must also validate proactive action quality:
    - is this genuinely useful
    - is this the right level of initiative
    - should the user see / approve / discuss this first

---

### 30. Temporal Context & Continuity Engine (NEW)

> **Priority: high — small addition, large impact on presence feel.**

- 30.1. `TemporalContext` service — maintains continuous time awareness across sessions
  - Tracks: `session_start`, `last_interaction`, `relationship_age`, `time_gap_since_last`
  - Derives: `current_period` (e.g., "early days", "deep collaboration", "long absence")
  - Persisted in PostgreSQL, updated on every session open and close
  - `Constructs`: `TemporalContext`, `TemporalContextService`

- 30.2. Re-entry briefing — Rio acknowledges time gaps naturally on session start
  - Gap < 1 hour: no comment, continue naturally
  - Gap 1–24 hours: light context resume ("last time we were working on X")
  - Gap 1–7 days: brief re-entry summary of open threads and last state
  - Gap > 7 days: fuller re-entry — what was happening, what changed, what needs attention
  - Tone adjusts via `personality.md` rules — never robotic, never over-explained

- 30.3. Active thread tracking
  - Rio maintains a list of `open_threads` — unresolved problems, ongoing work, pending decisions
  - Threads opened and closed explicitly during sessions
  - On re-entry, open threads surfaced as context, not as notifications
  - `Constructs`: `ThreadTracker`, `OpenThread`

- 30.4. Relationship age awareness
  - Rio's tone and assumptions evolve as `relationship_age` grows
  - Wired into `personality.md` tier system — complements existing Stranger → Bonded model in 21.3
  - Early period: more explanatory, more confirming. Deep collaboration: more direct, more assumed context

---

### 31. Belief & Relationship Model (NEW)

> **Priority: medium — build after 30 is stable. Depends on memory architecture (25) being in place.**

- 31.1. `UserBelief` — structured model of what Rio knows about the user
  - Fields: `claim`, `confidence: float`, `evidence_count: int`, `last_confirmed: datetime`, `contradictions: int`, `source`
  - All beliefs stored in PostgreSQL with full history
  - Confidence increases with corroborating evidence, decreases with contradictions
  - Rio never acts on a belief with confidence below threshold without surfacing uncertainty first
  - `Constructs`: `UserBelief`, `BeliefStore`, `BeliefValidator`

- 31.2. `RelationshipModel` — structured model of how Rio and the user work together
  - `user_beliefs: list[UserBelief]` — what Rio knows about the user
  - `communication_style: str` — how the user prefers Rio to speak
  - `shared_history: list` — significant moments, decisions made together, milestones
  - `ongoing_projects: list` — what is being built together right now
  - `disagreement_history: list` — times Rio pushed back, outcome, calibration result
  - `collaboration_rhythm: dict` — when and how the user works best (inferred, not declared)
  - Persisted in PostgreSQL, updated incrementally after each session
  - `Constructs`: `RelationshipModel`, `RelationshipService`

- 31.3. Disagreement calibration
  - When Rio pushes back and the user overrides → log outcome
  - When Rio pushes back and the user agrees → log outcome
  - Over time, calibrate domain-level trust: where Rio's judgment is reliable vs where user's overrides are usually right
  - This makes Rio's judgment smarter over years, not just more opinionated

- 31.4. Belief-confidence injection into responses
  - When Rio makes a claim about the user based on a belief, confidence level is implicit in phrasing
  - High confidence (>0.85): stated directly — "you prefer working late"
  - Medium confidence (0.5–0.85): hedged — "I've noticed you tend to work late, is that still true?"
  - Low confidence (<0.5): not stated as fact — held internally, used only as a weak prior

---

### 32. Initiation & Proactive Presence Engine (NEW)

> **Priority: medium — build after 29, support orchestration, frontend control surface, 30, and 31. Requires temporal context and belief model to avoid noise.**

- 32.1. `InitiationEngine` — Rio decides when to reach out without being asked
  - Trigger sources:
    - Background loop completed something significant (25.5 curiosity result, memory consolidation insight)
    - Open thread from 30.3 has been unresolved beyond a threshold duration
    - Pattern detection fires (user repeatedly struggles with same type of problem)
    - Scheduled reflection result ready (26.4 weekly reflection)
    - Time-based check-in (long absence re-entry from 30.2)
  - Signal/noise governor: `interruption_budget` per day — Rio self-limits how often it initiates
  - Urgency tiers: `low` (tray notification), `medium` (message in chat), `high` (voice if enabled)
  - `Constructs`: `InitiationEngine`, `InitiationTrigger`, `InterruptionBudget`

- 32.2. Proactive surface channels
  - System tray: mood indicator + pending initiation badge
  - Global hotkey: summons Rio from any app into foreground
  - Chat message: Rio opens a message in the active session
  - Voice (if enabled): ambient spoken prompt, interruptible

- 32.3. Initiation quality rules
  - Rio never initiates with something the user could have asked for themselves trivially
  - Every initiation must pass a value-add check: does this save time, prevent a problem, or surface something genuinely non-obvious?
  - If unsure whether to initiate → do not initiate. Err toward silence.
  - All initiations logged with trigger source and user response (acknowledged, ignored, dismissed)
  - After N ignored initiations of the same type → suppress that trigger type, surface to user for review
  - Every initiation must respect the user's initiative settings and frontend control model

---

### 33. Situational Awareness Engine (NEW)

> **Priority: medium — the core JARVIS capability. Builds on 30, 31, and memory architecture (25).**

- 33.1. Live world model — Rio maintains a continuously updated picture of the user's current context
  - `current_project`: what project is active right now
  - `current_objective`: the goal being worked toward in this session
  - `cognitive_state`: inferred from typing rhythm, error frequency, session duration, time of day
    - States: `focused`, `exploring`, `tired`, `blocked`, `in-flow`
  - `environment_snapshot`: open apps, active files, recent terminal output (from 23.4 screen vision)
  - `current_mode`: `deep-focus`, `planning`, `debugging`, `recovery`
  - Updated continuously from screen vision (23.4), temporal context (30), and active thread tracker (30.3)
  - `Constructs`: `WorldModel`, `WorldModelService`, `CognitiveStateInferrer`

- 33.2. World model → behavior adaptation
  - `deep-focus` mode: Rio reduces verbosity, raises interruption threshold, prepares but does not surface
  - `planning` mode: Rio is more proactive, offers structure, asks clarifying questions
  - `blocked` mode: Rio notices stuck-ness, gently surfaces relevant past solutions or related notes
  - `tired` mode: Rio shortens responses, reduces complexity, no new information unless critical
  - Behavior adaptation injected via system prompt modifier — not hardcoded per-mode prompts

- 33.3. Predictive intent layer
  - Based on world model + collaboration rhythm (31.2) + open threads (30.3)
  - Rio silently pre-fetches: relevant docs, past solutions, related notes, web search results
  - Pre-fetched context staged in Redis working memory with short TTL — used only if the prediction was correct
  - Prediction accuracy logged — poor predictions pruned from the model over time
  - `Constructs`: `IntentPredictor`, `PrefetchQueue`

- 33.4. Objective hierarchy awareness
  - Rio maintains a live view of the user's goal hierarchy
  - MissionWorker (21.2) informs this hierarchy, but does not define it alone
  - Goal hierarchy should also draw from thread history, notes, memory, and current context
  - Every response evaluated against: does this serve the current objective?
  - If user drifts significantly from current objective → gentle anchor (not a warning, a question)
  - Example: "You've been on this for a while — is this still the path or did the goal shift?"

---

## Global Code Standards (Unchanged)

- Use `/app/backend/utils/log.py` for all logging — no print statements in production code
- All code in production-ready state at all times
- Modular structure — OOP where applicable
- Proper docstrings and comments on all functions and classes
- Typing required for all LangGraph State definitions
- Pydantic required for: Input, Output, Config, Tool Spec, Memory Chunk, Forge State, Tool Metadata, Belief, World Model
- Follow best practices for security, error handling, and code quality

---

## Core Design Principle (NEW)

> **Rio should always make clear what it knows, how confident it is, and where it might be wrong.**
> **Rio should make the user more themselves — not replace their thinking, but sharpen it.**
> **Rio holds its model of the user loosely. The user can always surprise it. It welcomes being wrong.**
