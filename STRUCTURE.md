Full system workflow:
```
flowchart TB
  %% Entry Points
  subgraph Entry["Entry Points"]
    UI["Streamlit UI"]
  end

  %% Frontend
  subgraph Frontend["Frontend Layer"]
    Auth["Auth UI/Session"]
    ChatUI["Chat + Controls"]
  end

  %% Backend Core
  subgraph Core["Backend Core"]
    AgentService["AgentService"]
    Config["AgentConfig"]
    Workflow["LangGraph Workflow"]
    LLM["LLM Registry + Selected Model"]
  end

  %% Tools
  subgraph Tools["Tooling Layer"]
    WebTool["WebSearchTool (Tavily)"]
    SQLTool["SQLTool"]
    RAGTool["VectorDBTool (Qdrant)"]
    HyDE["HyDE Tool"]
    Expand["Query Expansion Tool"]
  end

  %% RAG Pipeline
  subgraph RAG["RAG Pipeline"]
    Ingest["Ingestion Service"]
    Retrieve["Retrieval Service"]
    Rerank["Rerank Service"]
  end

  %% Persistence
  subgraph Data["Data & Storage"]
    Postgres["Postgres (SQLAlchemy Models)"]
    Checkpointer["LangGraph Postgres Checkpointer"]
    Qdrant["Qdrant Vector Store"]
    FileStore["File Storage / OCR inputs"]
  end

  %% Main flow
  UI --> Auth --> ChatUI
  ChatUI --> Config --> AgentService
  AgentService --> LLM
  AgentService --> Workflow

  %% Workflow -> tools
  Workflow --> WebTool
  Workflow --> SQLTool
  Workflow --> RAGTool

  %% RAG tool -> pipeline -> Qdrant
  RAGTool --> Retrieve --> Rerank --> Qdrant
  RAGTool --> Ingest --> Qdrant
  Ingest --> FileStore

  %% Extra RAG tools
  AgentService --> HyDE --> RAGTool
  AgentService --> Expand --> RAGTool

  %% Persistence
  Workflow -. checkpoints .-> Checkpointer
  Workflow --> Postgres
  SQLTool --> Postgres

  %% Results
  Workflow --> ChatUI
```

LangGraph Workflow:
```
flowchart LR
  Start([Start]) --> Prepare["prepare"]
  Prepare --> Route["route"]
  Route --> Plan["plan"]
  Plan --> RunAgent["run_agent"]
  RunAgent --> Verify["verify"]
  Verify --> Finalize["finalize"]
  Finalize --> End([End])

  %% Persistence hooks
  Prepare -. checkpoint .-> StateStore["LangGraph Postgres Checkpointer"]
  Route -. checkpoint .-> StateStore
  Plan -. checkpoint .-> StateStore
  RunAgent -. checkpoint .-> StateStore
  Verify -. checkpoint .-> StateStore
  Finalize -. checkpoint .-> StateStore

  RunAgent -. run_meta .-> RunStore["run_service -> Postgres"]
```

Data model diagram (current ORM entities):
```
erDiagram
  USER ||--|| USER_PROFILE : has
  USER ||--o{ THREAD : owns
  THREAD ||--o{ MESSAGE : contains
  THREAD ||--o{ RUN : has
  MESSAGE ||--o{ TOOL_USAGE : references
  USER ||--o{ AUDIT_LOG : writes

  USER {
    uuid id
    string username
    string email
    string hashed_password
    enum role
    datetime created_at
    datetime updated_at
  }

  USER_PROFILE {
    uuid id
    uuid user_id
    string full_name
    string phone
    string address
    string company
    string job_title
    string locale
    datetime created_at
    datetime updated_at
  }

  THREAD {
    uuid id
    uuid user_id
    string title
    enum status
    datetime created_at
    datetime updated_at
  }

  MESSAGE {
    uuid id
    uuid thread_id
    string run_id
    enum role
    text content
    datetime created_at
  }

  RUN {
    string id
    uuid thread_id
    string mode
    string model_name
    enum status
    text error
    datetime started_at
    datetime ended_at
  }

  TOOL_USAGE {
    uuid id
    uuid message_id
    string tool_name
    enum status
    text error_message
    datetime created_at
  }

  AUDIT_LOG {
    uuid id
    uuid user_id
    string action
    json details
    datetime created_at
  }
```

Checkpoint store (LangGraph):
```
flowchart LR
  WorkflowState["GraphState (ephemeral)"] --> Checkpointer["PostgresSaver"]
  Checkpointer --> CheckpointTables["langgraph_checkpoints_* tables"]
  WorkflowState -. scope .-> Scope["state_scope: thread | session/run"]
```

Ingestion pipeline data diagram:
```
flowchart LR
  File["Source File (PDF/MD/JSON/CSV/HTML/DOCX)"] --> Extract["Content Extraction / OCR"]
  Extract --> Normalize["Normalize to Markdown"]
  Normalize --> Document["Document (normalized text)"]
  Document --> Chunk["Chunk (recursive/semantic)"]
  Chunk --> Metadata["Metadata (source, page, chunk, type)"]
  Chunk --> Embed["Embedding (dense + sparse)"]
  Embed --> Point["Vector Point (id, vectors, payload)"]
  Metadata --> Point
  Point --> Qdrant[("Qdrant Collection")]
```

SQL database schema (current structure):
```
erDiagram
  USER ||--|| USER_PROFILE : has
  USER ||--o{ THREAD : owns
  THREAD ||--o{ MESSAGE : contains
  THREAD ||--o{ RUN : has
  MESSAGE ||--o{ TOOL_USAGE : references
  USER ||--o{ AUDIT_LOG : writes

  USER {
    uuid id
    string username
    string email
    string hashed_password
    enum role
    datetime created_at
    datetime updated_at
  }

  USER_PROFILE {
    uuid id
    uuid user_id
    string full_name
    string phone
    string address
    string company
    string job_title
    string locale
    datetime created_at
    datetime updated_at
  }

  THREAD {
    uuid id
    uuid user_id
    string title
    enum status
    datetime created_at
    datetime updated_at
  }

  MESSAGE {
    uuid id
    uuid thread_id
    string run_id
    enum role
    text content
    datetime created_at
  }

  RUN {
    string id
    uuid thread_id
    string mode
    string model_name
    enum status
    text error
    datetime started_at
    datetime ended_at
  }

  TOOL_USAGE {
    uuid id
    uuid message_id
    string tool_name
    enum status
    text error_message
    datetime created_at
  }

  AUDIT_LOG {
    uuid id
    uuid user_id
    string action
    json details
    datetime created_at
  }
```

SQL database connection link:
```
postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}
```

Connection flow:
```
flowchart LR
  Env[".env / ENV vars"] --> Config["AppConfig.from_env()"]
  Config --> Engine["create_engine(database_url)"]
  Engine --> Session["SessionLocal (SQLAlchemy)"]
  Session --> Postgres[("Postgres")]
```

