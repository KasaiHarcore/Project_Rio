## Phase 1: Functional Logic (Core)

The `src/core/` layer establishes the foundational scaffolding, lifecycle hooks, concurrent processing pools, infrastructure wiring, and static configurations required to boot the FastAPI application securely before any business logic is ever executed.

### `app.py`

This file acts as the entry point and central configuration hub for your backend API.

Application Lifecycle Management (lifespan):
- **Startup**: It runs necessary background tasks, starts the concurrency manager, and wires up important dependencies (like injecting the cache service into the chat_history_service).
- **Shutdown:** It gracefully tears down the concurrency manager and runs any necessary cleanup tasks when the server stops.

Middleware Pipeline Configuration:
- **CORS**: Configures cross-origin resource sharing so that your frontend can securely communicate with the API.
- **Request Tracking**: Adds a RequestIdMiddleware to attach a unique ID to every request, making logging and debugging much easier.
- **Security**: Adds SecurityHeadersMiddleware to ensure standard security practices are followed for HTTP headers.

Global Exception Handling:
- **Custom Application Errors**: It catches app's custom exceptions (like NotFoundError, AuthenticationError, RateLimitError) and standardizes how they are sent back to the client as clean, predictable JSON responses with the correct HTTP status codes.
- **Validation Errors**: Takes raw Pydantic validation errors (when a user sends bad data) and reformats them into a friendly 422 Unprocessable Entity response specifying exactly which fields were invalid.
- **Unhandled Errors (Safety Net)**: Catches any unexpected crashes and returns a standard 500 Internal Server Error without leaking sensitive stack traces to the end user.

Observability: Automatically generate metrics (like request latency and error rates) and exposes them on a /metrics endpoint for monitoring.

Routing: imports all your actual API endpoints from routers.v1_router and mounts them under the /api/v1 prefix.

### `concurrency.py`

This file acts as the Application-Wide Concurrency Manager, allowing the async FastAPI app to efficiently offload heavy or synchronous work without blocking the main event loop.

Execution Pools and Helpers (Async to Sync Bridging):
- **Thread Pool**: Provides a managed pool of threads for blocking I/O tasks (like synchronous database calls).
- **Process Pool**: Provides a managed pool of separate processes for CPU-heavy tasks (like document chunking).
- **Batch Processing**: Helpers to run multiple blocking functions concurrently in parallel.
- **Fire-and-Forget**: Helpers to instantly kick off isolated background work.

**Technical / Architectural Methods Used:**
- **Singleton Pattern**: The `concurrency_manager` is instantiated globally at the module level to ensure only one thread/process pool manages the whole app.
- **Resource Pooling**: Maintains a fixed number of threads/processes configured by the environment to prevent CPU starvation.

### `dependencies.py`

This file is the central wiring hub that passes database sessions, cached lookups, and configuration into your individual endpoints. It also acts as the primary gatekeeper for user authentication.

Role-Based Security & JWT Validation:
- **Token Extraction**: Reads and decodes JWT (`access` tokens) from incoming HTTP Authorization headers.
- **User Resolution**: Looks up the user ID in the Redis Cache first (identity map) and falls back to the Postgres Database if missing.
- **Permission Guards**: Enforces role restrictions (like `require_admin`).

Component Factories:
- **Repository Initialization**: Wires active Postgres `Session` connections into Database Repositories.
- **Service Initialization**: Wires Repositories and external caches into Business Logic Services.

**Technical / Architectural Methods Used:**
- **Dependency Injection (DI) Graph**: Uses FastAPI's `Depends` system to inject dependencies at runtime instead of hardcoding imports. This makes mocking components for testing extremely easy.
- **Identity Map & L2 Caching**: Uses a two-tier lookup (Redis -> Postgres) for frequent user token checks to avoid hitting the DB on every single HTTP request.
- **Role-Based Access Control (RBAC)**: Defines strict role boundaries via the `require_roles` closure factory.
- **Factory Pattern**: Automates the instantiation of complex services like `get_note_service()`.

### `exceptions.py`

This file defines a clean, predictable hierarchy of custom error types for the application.

Error Hierarchy:
- **DatabaseError**: Failures in SQL connections or transactions.
- **NotFoundError**: Triggered when a requested resource doesn't exist.
- **ValidationError**: Triggered when incoming JSON or schemas are malformed.
- **Authentication/Authorization Error**: Triggered on bad passwords or missing permissions.
- **RateLimitError**: Triggered when the user hits an endpoint too many times.
- **WorkflowError**: Triggered when the AI Agent encounters an execution failure.

**Technical / Architectural Methods Used:**
- **Custom Exception Classes**: Inheriting from a base `AppException` so the global exception handler in `app.py` can automatically convert Python errors into consistent JSON API responses.

### `middleware.py`

Provides invisible processing layers that wrap around every single incoming HTTP request and outgoing response.

Request Processing:
- **Security Headers**: Injects standard HTTP security policies into the response (like preventing the site from being embedded in an iframe).
- **Request Tracking**: Generates a unique 12-character ID (UUID) for the request if the client didn't provide one, attaching it to logs and the response header. 
- **Process Timing**: Automatically calculates how many milliseconds the server took to process the request and appends `x-process-time-ms`.

**Technical / Architectural Methods Used:**
- **Pure ASGI Middleware**: Avoids FastAPI/Starlette's standard `BaseHTTPMiddleware` overhead by writing directly to the low-level ASGI specification (acting on raw `scope`, `receive`, and `send` events) to maximize request throughput.

### `scheduler.py`

A background task supervisor that periodically wakes up to check if any automated tasks or scheduled events need to run.

Automation Loop:
- **Interval Checking**: Wakes up every 60 seconds.
- **Execution**: Instantiates a fresh database session, checks `AutomationService` for any "due" automations, executes them, and either commits or rolls back the transaction.

**Technical / Architectural Methods Used:**
- **Background Daemon Polling**: Uses a basic Python `threading.Thread(daemon=True)` instead of a heavy library like Celery to achieve background task execution.
- **Thread-safe Signaling**: Uses `threading.Event()` to securely signal the thread to stop immediately if the web server shuts down.

### `settings.py`

The centralized environment variable definitions and configuration parser. 

Application Modules:
- **AppConfig**: Core settings (Database connection strings, Pool settings, API Keys).
- **AgentConfig / VectorDBConfig**: Settings specific to the AI reasoning loop (Max tokens, retries, RAG chunk sizes, extraction limits).
- **RedisConfig / CorsConfig / OAuthConfig**: Security and network layer variables.

**Technical / Architectural Methods Used:**
- **Dataclasses & Environment Parsing**: Maps raw OS environment strings into strongly typed Python objects using `os.getenv` with sensible system defaults.
- **Lazy Initialization / Singleton Pattern**: Evaluates `.env` and initializes configuration dataclasses only when first requested (`get_app_config()`).

### `startup.py`

Contains the deterministic boot sequence triggered by `app.py` when the server turns on.

Lifecycle Sequence:
- **Schema Validation**: Validates the `.env` settings to crash early if something critical is missing.
- **Resource Warm-Up**: Spins up necessary systems like the embedding models for vector databases or database tables (if auto-create is turned on).

**Technical / Architectural Methods Used:**
- **Parallel I/O Initialization**: Connects to Postgres, Qdrant (Vector DB), and Redis at the exact same time using `ThreadPoolExecutor` to significantly speed up boot time.
- **Fail-Fast Methodology**: Intentionally crashes the application immediately if critical infrastructure logic is unreachable.

### `ws_manager.py`

Tracks all active, live WebSocket connections to power real-time updates to the frontend dashboard.

Connection Tracking:
- **Session Mapping**: Groups active websocket connections by `user_id`. (A user with two browser tabs open will have multiple sockets mapped).
- **Broadcasting & Direct Messaging**: Exposes methods to send a JSON payload to a specific user or broadcast to everyone.
- **Heartbeat Checks**: Sends an empty "ping" occasionally to see if the client's internet connection quietly died without properly closing the socket.

**Technical / Architectural Methods Used:**
- **Pub/Sub (Publisher/Subscriber) Pattern (Basic)**: A localized system to publish events to connected clients.
- **Singleton Pattern**: Defined globally as `ws_manager` to maintain state across all web routes.
- **Asynchronous Locking**: Uses `asyncio.Lock()` to prevent race conditions if multiple streams try to connect or disconnect a user at the exact same millisecond.

---

## Phase 2: Functional Logic (Services)

The `src/services/` layer acts as the centralized nervous system encapsulating all pure business logic. It sits completely separated from external protocols (like HTTP or Websockets) and safely interacts with databases (via Repositories) or third party infrastructure (via LLMs/External APIs) on behalf of the user.

### `admin_service.py`

Handles dangerous, system-wide administrative destructive operations like clearing all databases and vector collections.

System Reset:
- **Destructive Formatting**: Drops SQL tables, manually wipes un-dropped ENUMs from PostgreSQL, and truncates the Qdrant Vector database remotely.

**Technical / Architectural Methods Used:**
- **Monolithic / System-level Reset**: Directly connects to lower-tier SQL engines bypassing Repositories entirely.

# agent_service.py

Provides the clean interface bridging standard HTTP API requests to the complex Multi-Agent AI Supervisor logic.

Execution Control:
- **Synchronous Execution**: Runs a complete LangGraph evaluation until finished, extracting output logs and cost token stats.
- **Streaming Execution**: Yields Server-Sent Events (tokens, supervisor decisions, tool starts) from the Graph sequentially.

**Technical / Architectural Methods Used:**
- **Supervisor-Worker / Multi-Agent Pattern**: Validates and wires inputs directly into the LangGraph state machine so reasoning loops can trigger multiple sub-models.
- **Streaming Pipeline**: Uses Python `yield` generators natively to push byte chunks to web sockets/HTTP protocols without holding response objects in memory.

# auth_service.py

The central authority for User login, registration, and password hashing logic.

Account Actions:
- **Verification**: Validates Passwords via bcrypt and prevents duplicate user/email registrations.
- **OAuth Resolution**: Handles "Google/GitHub Account Linking"—tying a new provider login to an already existing local Email account automatically.

**Technical / Architectural Methods Used:**
- **Data Access Object (DAO) Isolation**: Strictly uses `UserRepository` without ever executing a raw `Session.query()`. This encapsulates the database entirely.
- **Cryptographic Salting / Hashing**: Uses rigorous one-way hashing techniques (`get_password_hash`) to ensure plaintext passwords never touch Ram/Disk.
- **Audit Trails**: Triggers mandatory insertions into an `AuditLogRepository` whenever high-privilege access occurs regardless of success or failure.

# chat_history_service.py

Handles the persistent storage of User Threads and Messages exclusively to PostgreSQL.

Message Management:
- **Title Generation**: Automatically names a Thread based on the client's first User prompt.
- **Context Buffering**: Generates exactly the length of messages needed for the LLM's next input round (e.g. keeping only the last 20 messages).
- **Data Compaction**: When memory window gets too large, automatically tells the LLM to summarize past turns, saves a new `[SUMMARY]` token, and hard deletes old raw messages to save Database size indefinitely.

**Technical / Architectural Methods Used:**
- **Write-Through Caching**: Saves messages to PostgreSQL while simultaneously injecting heavily-requested subsets directly to Redis.
- **L2 / Identity Map Caching**: Speeds up Thread resolution dramatically so the database is accessed less often.
- **State Compaction Pattern**: Automatically prunes conversation trees safely via contextual summarization.

# chat_service.py

Business layer completely extracted out of the `/api/v1/chat` routers to keep HTTP handlers ultra-clean.

Chat Initialization:
- **Setup Prep (`prepare_chat`)**: Resolves workspace code references, calculates XP rewards, invalidates old user dashboards in Redis smoothly, applies correct LLM api-keys per user, and returns a unified `ChatPrepResult` for streaming.

**Technical / Architectural Methods Used:**
- **Facade Pattern**: Hides five different sub-services (XP, Settings, Cache, Identity, Memory) behind one clean API call (`prepare_chat`), severely reducing complexity at the REST Endpoint layer.
- **Cache Invalidation Strategy**: Surgically invalidates ONLY the affected Redis dashboard tokens when a user speaks so live updates render instantly.

# artifact_service.py

Handles the creation and versioning of AI-generated work products (code files, documents, scripts).

Artifact Versioning:
- **Hierarchical Linking**: When an artifact is updated, it creates a new version while storing a pointer (`parent_id`) to the previous state, keeping a full audit trail of edits.

**Technical / Architectural Methods Used:**
- **Hierarchical Versioning (Linked List)**: Implements history traversal through a DB-level Linked List allowing UI users to "roll back" to any previous code generation.

# audio_service.py

Converts study materials (flashcards, notes) into conversational spoken-word podcast scripts and literal MP3 audio sequences.

Audio Synthesis:
- **Background Generation**: Translates heavy TTS (Text-to-Speech) generation using the Qwen3 engine.
- **Content Aggregation**: Pulls disjointed DB objects, pushes them through an LLM to generate a natural teacher/student dialogue script.

**Technical / Architectural Methods Used:**
- **Asynchronous Job Queue**: Uses `concurrency_manager.submit_fire_and_forget` to offload massive audio processing times from the web server thread.
- **State Machine**: Employs PENDING -> GENERATING -> READY statuses to track background operations without blocking the client.

# automation_service.py

A Cron-based supervisor allowing the AI to run tasks automatically in the future without the user being logged in.

Scheduled Execution:
- **Time Parsing**: Converts user-friendly cron expressions across specific timezones.
- **Agent Triggers**: Wakes up an isolated LangGraph execution under the user's ID at the specified intervals.

**Technical / Architectural Methods Used:**
- **Polling Execution**: Relies on `croniter` and a background thread to calculate next_run intervals, allowing exact system-level scheduled jobs from DB rows.

# collection_service.py

Provides folder-like management to group Sticky Notes together.

Organization Methods:
- **Aggregate Counting**: Requests exact counts of notes inside a collection instantly upon query.

**Technical / Architectural Methods Used:**
- **Hierarchical Mapping (CRUD)**: Simple Data Access mapping that joins multiple DB entities dynamically on query.

# dashboard_service.py

A unified aggregator that builds the landing page "Briefing" when the user logs in.

Context Aggregation:
- **Dynamic Greeting**: Builds a text prompt taking into account how many days it's been since the user logged in, their urgency on missions, and Rio's "mood".
- **Metric Stitching**: Queries raw SQL statistics on messages, thread completions, and profile data to build visualization arrays.

**Technical / Architectural Methods Used:**
- **Service Aggregator Pattern**: Does not own its own DB tables; instead it acts as an overarching collector calling X, Y, and Z repositories simultaneously to build a single "Dashboard View".

# document_service.py

Basic integration wrapping the `DocumentRepository` for user-uploaded PDFs and Text files.

File Ingestion Tracker:
- **Upload States**: Tracks if a document was successfully chunked and vectored, or if the PDF parser crashed (ERROR).

**Technical / Architectural Methods Used:**
- **Data Access Object (DAO) CRUD**: A thin wrapper primarily enforcing standard validation and state progression over file entities.

# emotional_engine.py

The core algorithmic driver behind the "Living AI" persona, altering its personality and warmth dynamically.

Emotional Calculus:
- **Affinity Decay**: Drops "Energy" points algebraically over time if the user is absent for 48+ hours.
- **Sentiment Triggers**: Passes user messages through a fast LLM extraction to categorise if the user is being "Negative/Frustrated" or "Positive/Grateful".

**Technical / Architectural Methods Used:**
- **Finite State Machine (FSM)**: Strictly defines transition grids (e.g. state `Happy` receiving `Negative` input transitions to state `Neutral` reducing affinity by -1).
- **Mathematical Decay Modeling**: Simulates a lifelike decay over time (`ENERGY_DECAY_RATE`) independent of direct database updates.

# flashcard_service.py

Domain logic for the Spaced Repetition study application.

Study Scheduling:
- **SM-2 Algorithm Implementation**: Identical mathematical algorithm used by Anki to determine the exact `interval_days` until you see a flashcard again based on your rating from 0-5.
- **Automated Generation**: Automatically pulls Note entities into memory and asks the LLM to generate Q&A flashcards out of them.

**Technical / Architectural Methods Used:**
- **Algorithmic Scheduling (SM-2)**: Applies exact spaced repetition mathematics to delay information presentation.
- **Adaptive Context Loading**: Re-queries the `EmotionalEngine` during a flashcard session to reduce difficulty bounds if the character detects the user is tired or frustrated.

# mission_service.py

The strict "Source of Truth" for Mission (Task) tracking, stopping the LLM from making illegal state mutations.

Goal Transitions:
- **Step Verification**: Allows turning partial sub-steps of a mission on and off, automatically completing the Mission if all steps hit 100%.
- **LLM Boundary Protection**: Forces LLM-extracted updates to discard forbidden modification requests (like arbitrarily changing a mission status without actually resolving its steps).

**Technical / Architectural Methods Used:**
- **Strict FSM Validation (State Transitions)**: explicitly blocks transitioning from `COMPLETED` directly back to `DRAFT`, ensuring the LLM cannot cause logic breaks.
- **Idempotency Guarantees**: Forces repetitive save commands from the Agent to safely "do nothing" instead of crashing.

# note_link_service.py

Handles bidirectional `[[Obsidian Style]]` linking between files.

Graph Generation:
- **Content Parsing**: Reads markdown content actively to find `[[ ]]` expressions, compares it to the database, and adds/deletes SQL link references dynamically using diffing.
- **Node-Edge Visualization**: Generates raw Node/Edge graphing data arrays for the visual frontend.

**Technical / Architectural Methods Used:**
- **Graph Parsing & Sync**: Extracts raw text blocks and transforms them into relational entity mappings without user intervention.

# note_service.py

Operations for persistent sticky notes, saving them to standard postgres rows but also syncing them.

Bi-directional Backup:
- **Disk Persistence**: Besides SQL, it aggressively dumps a raw `.md` copy of the note to the `storage/notes` directory on the physical hard drive.
- **Vector Upserting**: Automatically pushes new sticky notes into Qdrant so the LLM remembers them in standard Chat.

**Technical / Architectural Methods Used:**
- **Active Record Style Syncing**: Every CRUD action immediately triggers a cascaded file-system sync + vector db sync automatically behind the scenes.

# os_control_service.py

The gatekeeper to the physical OS, deciding what the AI is legally allowed to execute.

Risk Management:
- **Execution Routing**: Routes `cd`/`grep` to the Shell, or `click`/`scroll` to the Browser.
- **Pre-Classification**: Calculates the threat tier (e.g. `rm -rf` = Tier 3) and temporarily pauses the execution sequence until the web UI confirms approval.

**Technical / Architectural Methods Used:**
- **System Gatekeeper / Sandbox Wrapper**: Hides the dangerous physical controllers (`BrowserController`, `PTYSession`) behind extreme scrutiny preventing prompt-injections from wiping the system.

# settings_service.py

Manages user config, API Keys, and Onboarding settings.

Key Governance:
- **Encryption Overrides**: Scans incoming JSON parameters for API keys, encrypts them securely using server-side keys, and stores the cipher text.
- **Masking**: Sends `sk-••••••` back to the frontend instead of the real payload.

**Technical / Architectural Methods Used:**
- **Secret Management**: Implements symmetric encryption (`cryptography` fernet) and guarantees plaintext keys never remain un-encrypted in the DB layer.

# sql_schema_service.py

Calculates the exact layout of PostgreSQL to feed to the LLM for the `.sql` execution feature.

Schema Discovery:
- **Introspection**: Connects to SQLAlchemy natively and determines all primary/foreign key connections without explicitly querying data (zero-data-leak mapping).
- **Tiered Summarization**: Only provides column datatypes for tables the LLM *needs* to know about to prevent blowing up the LLM token context size limit.

**Technical / Architectural Methods Used:**
- **Database Introspection**: Generates DB shapes programmatically instead of relying on manually written schemas.

# xp_service.py

A unified module to dish out experience points.

Level Progression:
- **Triangular Formulas**: Uses continuous formulas (e.g., `50 * Level * (Level - 1)`) to determine level rather than an arbitrary database staircase.
- **Event Triggers**: Grants arbitrary amounts on Document parsing, daily milestones, or task completions.

**Technical / Architectural Methods Used:**
- **Mathematical Progression Design**: Leverages algebraic scaling for purely UI gamification elements.
- **L2 Cache Write-Throughs**: Writes the XP updates instantly to Redis since XP increments trigger rapidly during conversation streams, minimizing DB latency.

---

## Phase 4: Functional Logic (Workflows)

The `src/workflows/` layer defines the multi-agent architecture powered by LangGraph. It is responsible for orchestrating LLM tool calling, handling memory integration, routing user requests to sub-agents, providing checkpointing/durability for Human-in-the-Loop interruptions, and streaming token-by-token feedback to the client.

### `executor.py`
* **High Level**: The main execution engine for running the LangGraph workflow.
* **Workflow Concept**: ReAct graph runner for both synchronous (`run_workflow`) and asynchronous streaming (`stream_workflow`) executions.
* **Technical/Architectural Methods Used**: 
  * **Event Protocol Morphing/Streaming**: Morphs LangGraph state transitions (`AIMessageChunk`, `ToolMessage`) dynamically into frontend-compatible events (`token`, `supervisor`, `worker`).
  * **Time-Travel Resumption**: Injects `checkpoint_id` to dynamically load a suspended workflow state when answering an interruption (e.g. `resume_sql_approval`).

### `react_graph.py`
* **High Level**: Defines the actual topology of the ReAct LangGraph agent.
* **Workflow Concept**: Defines the physical node connectivity of the LangGraph execution graph (e.g., `START -> input_guardrail -> planner -> agent <-> tools -> post_process -> output_guardrail -> END`). Replaces generic prebuilt agent utilities.
* **Technical/Architectural Methods Used**:
  * **Background Post-Processing**: Dispatches asynchronous threads on completion to automatically parse episodic memory (`memory_store.py`) and log mood updates into the `EmotionalEngine`.
  * **Pre-emptive Circuit Breaker**: Evaluates if the agent's recent message history repeats identical failing tool calls, triggering early termination to save costs and avoid infinite loops.

### `planner.py`
* **High Level**: Pre-computation triage layer to route LLM intent.
* **Workflow Concept**: Evaluates user queries via an LLM prior to the main agent being called. It computes an `instruction` and explicit list of `actions` (the exact tools required).
* **Technical/Architectural Methods Used**:
  * **Context-Window Minimization**: By deciding the tools first, it prevents the main ReAct agent from carrying the payload descriptions of 15+ sub-agents in its active prompt window, drastically dropping overhead token costs.

### `tool_registry.py`
* **High Level**: Manages descriptions and implementation guides for all tools in the system.
* **Workflow Concept**: Connects descriptive text definitions to functional tools and handles fallback logic between different sub-agents.
* **Technical/Architectural Methods Used**:
  * **Dual-Prompt Formatting**: Every entry holds a `description` (short, cheap text injected into the `planner.py` context) and a `guide` (long, detailed instructions on how to use the tool, only loaded if the planner enables that tool for the main agent).

### `checkpointer.py`
* **High Level**: Handles memory persistence and checkpointing so workflows can be paused and resumed.
* **Workflow Concept**: Wraps LangGraph's native PostgresSaver. Saves execution state between LLM turns securely into a PostgreSQL Database.
* **Technical/Architectural Methods Used**:
  * **Interruption Management**: Allows the graph pipeline to pause natively while waiting for user confirmation via SSE stream, guaranteeing the thread stays perfectly preserved until user input arrives.

### `memory_store.py`
* **High Level**: Memory integration for passing RAG contexts to the LLM.
* **Workflow Concept**: Handles vector database queries to inject context-aware memories dynamically into ongoing agent interactions.
* **Technical/Architectural Methods Used**:
  * **Semantic Fallback**: Handles queries dynamically without needing fixed relational database lookups. 

### `tools/delegation_tools.py`
* **High Level**: Connects the Supervisor graph to the respective sub-agent subgraphs.
* **Workflow Concept**: Provides standard LangChain `@tool` entry points (e.g. `delegate_note_task`, `delegate_mission_task`) that the Supervisor agent is legally allowed to invoke.
* **Technical/Architectural Methods Used**:
  * **Hierarchical Spawning**: Instead of raw python functions, each tool literally spawns a separate synchronously-compiled instance of another specific ReAct sub-agent (`build_mission_sub_agent()`), feeding it an exact constraint task.

### `guardrails/input_guardrail.py` & `guardrails/output_guardrail.py`
* **High Level**: Security and safety boundaries enforcing prompt structures.
* **Workflow Concept**: Validates the incoming network query payload and standardizes the exiting response payload strings before output.
* **Technical/Architectural Methods Used**:
  * **Deterministic PII Check**: Rejects any outgoing text returning Credit Cards, Passwords, SSN via regular expressions before the user can see it.
  * **System Leak Regex**: Automatically catches instances where the LLM attempts to regurgitate its core system prompt due to adversarial user instructions.

---

## Phase 3: API Presentation (Routers)

The `src/routers/` layer acts strictly as the "delivery mechanism." It is responsible for accepting HTTP/WebSocket connections, validating request bodies (via Pydantic), checking JWT/OAuth credentials, and immediately delegating business logic to the `services/` layer.

# __init__.py

Central API registry that dynamically mounts all router files under a unified `v1_router` so they can be attached to the main FastAPI app in a single command.

Endpoint Concept/Method:
- **Centralized Mounting**: Combines exactly 29 separate APIRouter instances into a single `v1_router` prefix.

**Technical / Architectural Methods Used:**
- **Router Aggregation**: Keeps `app.py` completely decoupled from HTTP path declarations.

# admin.py

Administrative endpoints for system diagnostics and role management.

Endpoint Concept/Method:
- **Metrics Polling**: Calculates active users, thread volumes, and system-wide stats dynamically.
- **Destructive Actions**: Triggers full SQL and Vector database resets.

**Technical / Architectural Methods Used:**
- **Role Verification**: Validates admin JWT roles before exposing sensitive metrics or triggering destructive actions.
- **Audit Logging**: Wraps security actions (like changing a user's role) in `audit_repo.create` tracking.

# artifact.py

Standard ReST CRUD interface for AI-generated artifacts.

Endpoint Concept/Method:
- **Download Streams**: Uses `fastapi.responses.Response` natively to serve string contents dynamically mapped to MIME types (like `application/octet-stream`).

**Technical / Architectural Methods Used:**
- **Data Access Wrappers**: Purely passes Pydantic JSON requests to the `ArtifactService` with strict UUID validation.

# audio.py

Triggers background TTS audio generation.

Endpoint Concept/Method:
- **Job Offloading**: Receives a generation request, returns `202 ACCEPTED` immediately, and tracks the job completion state.
- **Ranged Streams**: Delivers the generated `.mp3` bytes utilizing `FileResponse`, natively supporting range-requests in the browser.

**Technical / Architectural Methods Used:**
- **Asynchronous Handoff**: Moves heavy TTS workloads away from the web server thread using `concurrency_manager.submit_fire_and_forget`.

# auth.py

Handles the local authentication lifecycle.

Endpoint Concept/Method:
- **Token Pairing**: Returns an Access Token (short life) and a Refresh Token (long life).
- **Session Revocation**: Forces a logout by destroying the refresh token server-side via Redis.

**Technical / Architectural Methods Used:**
- **Rate Limiting**: Protects public login and register endpoints via a Redis sliding window to mitigate brute-force attempts.
- **JWT Cryptography**: Fully stateless, signed JWT tokens avoiding constant PostgreSQL hits on every request.

# automation.py

Allows users to CRUD cron-based background jobs and manually trigger immediate executions.

Endpoint Concept/Method:
- **Cron Management**: Wraps SQL logic to add/delete jobs.
- **Manual Launch**: Skips the cron threshold and executes an automation job explicitly.

**Technical / Architectural Methods Used:**
- **Job Delegation**: Simply acts as an HTTP trigger into the `AutomationService` executor.

# chat.py

The heaviest and most complex router, managing text generation streams for the LangGraph agent.

Endpoint Concept/Method:
- **ReAct Streams**: Converts python generator yields into explicit `data: {...}` lines for the web client.
- **History Retrieval**: Fetches standard Thread array objects and Memory representations.

**Technical / Architectural Methods Used:**
- **Server-Sent Events (SSE)**: Complies exactly with the **Vercel AI SDK v6 UIMessageStream** protocol. This forces unstructured text tokens *and* heavily structured JSON agent data (e.g., supervisor decisions, planning) into a single HTTP stream.
- **Yield Generators**: Keeps memory overhead extremely low by using Python `yield` loops directly over the SSE network buffer.

# collection.py

Simple ReST mapping for arranging Notes into folders.

Endpoint Concept/Method:
- **Folder Aggregations**: Queries the current state of collections, returning the dynamically joined counts of their contents.

**Technical / Architectural Methods Used:**
- **Standard ReST Mapping**: Maps `GET`, `POST`, `PATCH`, `DELETE` over HTTP statuses natively.

# dashboard.py

Aggregator endpoint that generates a personalized "Briefing" (messages, urgent missions, Rio's mood) when a user logs in.

Endpoint Concept/Method:
- **Unified Overview**: Triggers multiple distinct repository reads (Notes, Chats, Missions, Events) in a single API call to paint the frontend home screen.

**Technical / Architectural Methods Used:**
- **L2 Cache Hits (Read-Through Pattern)**: First checks Redis for a cached `DashboardStats` response; falling back to the massive 20-query calculation only if the cache expires, massively accelerating initial app load speeds.

# emotional.py

Exposes the "Living AI" emotional framework to the frontend.

Endpoint Concept/Method:
- **Interactions**: Handles explicit user interactions like "headpats" to manipulate the AI's affinity.
- **Graphing History**: Reads emotional transition histories to populate charts.

**Technical / Architectural Methods Used:**
- **State Mutation Endpoint**: Thinly wraps complex state-machine changes happening inside the `emotional_engine`.

# flashcard.py

ReST representations routing into the `FlashcardService` for SM-2 interval scheduling and automated generation.

Endpoint Concept/Method:
- **Algorithmic Review**: Receives a `0-5` quality score and triggers a math recalibration for the next review date.
- **AI Card Generation**: Connects the frontend to an LLM chain that converts Markdown notes into structured flashcards.

**Technical / Architectural Methods Used:**
- **Algorithmic Triggers**: Isolates the Spaced Repetition algorithms behind simple ReST calls.

# health.py

DevOps health probes pinging system infrastructure components.

Endpoint Concept/Method:
- **Liveness Probes**: Queries PostgreSQL, pinging Redis `PING`, and making a test inference request to the LLM.

**Technical / Architectural Methods Used:**
- **DevOps Monitoring Strategy**: Returns standard Kubernetes-friendly statuses (`healthy`, `degraded`, or `down`) so load balancers can track the application pulse.

# ingest.py

Downloads web pages natively to ingest them into the RAG Pipeline.

Endpoint Concept/Method:
- **URL Pipeline Initiation**: Accepts a URL, uses `httpx` to download the raw HTML/text, extracts chunk sizes, and creates a record.

**Technical / Architectural Methods Used:**
- **Side-Effect Orchestration**: Ingests into vector DB, triggers an XP award (`+15`), and forcefully invalidates the Dashboard cache in a single flow.

# jwks.py

Distributes standard OAuth key sets via endpoint.

Endpoint Concept/Method:
- **Public Key Exposure**: Calculates `.well-known/jwks.json` dynamically by analyzing the backend's RSA keys.

**Technical / Architectural Methods Used:**
- **OIDC Discovery Standard**: Cryptographically publishes the RS256 public keys so frontend clients and independent external services can verify the server's JWT signatures locally.

# knowledge.py

Receives physical file uploads (`.pdf`, `.md`) for the RAG pipeline.

Endpoint Concept/Method:
- **Multipart Form Data**: Accepts binary file streams alongside strategy settings.
- **Temp Storage**: Spools the uploaded byte stream to a `tempfile` dynamically before firing it to the Vector Database.

**Technical / Architectural Methods Used:**
- **File System Wrapper**: Prevents memory explosion by wrapping large memory uploads into temporary Unix disk space during processing. 

# logs.py

Exposes system application logs directly to the browser.

Endpoint Concept/Method:
- **Log Buffering**: Reads arrays natively from Python's logging hooks.
- **Live Tail Streaming**: Utilizes an `asyncio.Queue` block to immediately push new log additions down the wire.

**Technical / Architectural Methods Used:**
- **SSE Broadcast Optimization**: Unlike chunked encoding, this uses `text/event-stream` to push continuous backend Python logs directly into the Admin UI without polling.

# mcp.py

Management endpoints mapping Model Context Protocol definitions dynamically.

Endpoint Concept/Method:
- **Discovery**: Returns `MCPToolResponse` payloads describing dynamically installed tools on attached MCP servers.
- **Transport Registration**: Enables binding external servers over `stdio` or websocket transports.

**Technical / Architectural Methods Used:**
- **Dynamic Registry Routing**: Acts as the HTTP control plane for the internal MCP registry graph, allowing the frontend to enable internal React tools without code restarts.

# mission.py

Strict ReST logic for Task/Mission synchronization.

Endpoint Concept/Method:
- **Granular Updates**: Features `/{mission_id}/steps/{step_index}/toggle` to allow micro-updates of nested properties via URL parameters rather than sending massive JSON bodies.

**Technical / Architectural Methods Used:**
- **Nested Resource Mapping**: Strict API design mapping deep DB paths (`Mission -> Step`) into discrete HTTP verbs.

# note.py

Strict ReST logic for Markdown note synchronization.

Endpoint Concept/Method:
- **List and Filter**: Pulls notes linked to specific conversation threads or collections.
- **Todo Toggle**: Provides micro-endpoints to check/uncheck nested Markdown checkboxes.

**Technical / Architectural Methods Used:**
- **CRUD Operations**: Passes exact operations down to the `NoteService`.

# note_confirmation.py

Crucial endpoint handling Agent "Human in the Loop" (HITL) interruptions for Notes.

Endpoint Concept/Method:
- **Workflow Resumption**: Accepts manual "Approve" or "Reject" payloads when the agent tries to execute a dangerous Note rewrite or deletion. 

**Technical / Architectural Methods Used:**
- **Stream Protocol Morphing**: Forcefully resumes the paused LangGraph workflow and miraculously converts the resumed execution output back into a Vercel AI SDK SSE stream so the frontend doesn't disconnect.

# note_link.py

Node Mapping and Edge Creation Endpoint.

Endpoint Concept/Method:
- **Graphing Connections**: Exposes an array of 1-hop or global links between Markdown files.
- **Bulk Creation**: Dedicated endpoint for creating huge batches of links avoiding `N` REST calls.

**Technical / Architectural Methods Used:**
- **Network Aggregation**: Aggregates SQL join tables into D3.js compatible Graph schemas dynamically.

# oauth.py

Authenticates users via 3rd Party SSO Services.

Endpoint Concept/Method:
- **Code Exchange**: Intercepts callback queries from Google & GitHub, exchanging short-lived codes for User Profile JSONs securely.
- **User Merging**: Links the returned Github/Google emails and merges them with the local PostgreSQL user DB.

**Technical / Architectural Methods Used:**
- **OAuth 2.0 PKCE Flow Control**: Offloads user password management entirely to Microsoft/Google external architectures.

# onboarding.py

Configuration endpoint hit immediately upon Account Creation.

Endpoint Concept/Method:
- **Persona Storage**: Saves the user's defined "Directives" and "Tones" immediately to the database.

**Technical / Architectural Methods Used:**
- **Profile Seeding**: Hooks directly into the `SettingsService` bypassing standard updates to hard-initialize a profile entry.

# os_control.py

Receives commands directed at the physical host / virtual machine.

Endpoint Concept/Method:
- **Threat Classification**: `/os/shell/classify` determines the Risk Tier (1-4) of a bash command without executing it.
- **Physical Exections**: Forwards `click()`, `scroll()`, and `bash` commands to the host level.

**Technical / Architectural Methods Used:**
- **Action Scrutiny**: Forces HTTP callers to pre-classify shell scripts against regex models, dropping dangerous logic at the HTTP level.

# rio_response.py

A reactive generation endpoint.

Endpoint Concept/Method:
- **Contextual Framing**: Accepts JSON payloads outlining exactly what string to output based on a user action (e.g., logging in late at night).
- **Standalone Generation**: Forces a direct generation response bypassing LangGraph.

**Technical / Architectural Methods Used:**
- **Stateless LLM Invocation**: Uses raw LLM calls without initializing the massive multi-agent graph, enabling cheap, instantaneous greetings.

# search.py

General search aggregation targeting the physical external databases.

Endpoint Concept/Method:
- **Qdrant Routing**: Sends literal queries directly against `get_vector_db_tool()`.
- **Tavily Routing**: Fires requests outbound over the internet to extract real-world information.
- **Neo4j Routing**: Routes directly into the Cypher graph.

**Technical / Architectural Methods Used:**
- **Tool Mapping Wrappers**: Allows the Frontend Client to use the AI Tools (like Web Search) independently of the actual LangGraph agent.

# settings.py

CRUD representation patching User profiles and system configurations.

Endpoint Concept/Method:
- **Dynamic Field Updates**: Accepts partial `BaseModel` patches where `None` fields are deliberately ignored.

**Technical / Architectural Methods Used:**
- **State Normalization**: Returns both `UserSettings` and `UserProfile` objects in one unified response to prevent multiple UI waterfalls.

# sql_approval.py

Crucial endpoint handling Agent "Human in the Loop" (HITL) interruptions for SQL Generations.

Endpoint Concept/Method:
- **SQL Execution Resumption**: Halts `DROP`/`DELETE` LLM calls, waits for this endpoints signal, and resumes the database execution dynamically.

**Technical / Architectural Methods Used:**
- **Stream Protocol Morphing**: Identical to `note_confirmation.py`, it perfectly maps a resumed background process thread into an active HTTP generator stream.

# websocket.py

Fully bidirectional stateful communication channel.

Endpoint Concept/Method:
- **Real-Time Parity**: Accepts incoming message blobs and bounces back real-time LangGraph yields.
- **Authentication Timeout**: Kills connections if they don't produce a JWT within exactly 10 seconds of attaching.

**Technical / Architectural Methods Used:**
- **Stateful Lock Management**: Routes heavily on the `ws_manager` object to manage asynchronous loops tracking exactly which IP relates to which connected user, guaranteeing thread safety.
