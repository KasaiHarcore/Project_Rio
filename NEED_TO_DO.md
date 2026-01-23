Dev Route: (AGILE)
1. Establish Basic Foundation (**DONE**)
2. Integrate Streamlit (**DONE**)
3. Complete Basic RAG System Based on PDF Extraction (**DONE**)
4. Develop Advanced RAG Features
    4.1. Add SQL Database - PostgreSQL via SQLAlchemy (**DONE**)
    4.1.1. Implement CRUD Operations with Full Case Handling (**DONE**)
    4.1.2. Add Read/Retrieve Operations (**DONE**)
    4.1.3. Integrate Alembic (**DONE**)
    4.1.4. Resolve Connection Issues (**DONE**)
    4.1.5. Format Input/Output with Pydantic (**DONE**)
    4.2. Integrate Qdrant Vector Store (**DONE**)
    4.2.1. Add HyDE and Query Expansion (**DONE**)
    4.2.2. Add Sparse Embeddings and Hybrid Search (**DONE**)
    4.2.3. Add Cohere Reranker (**DONE**)
    4.2.4. Add OCR for Images and Scanned PDFs (Change to Image understanding -> Text information and save like other)
    4.3. Implement Web Search with Tavily (**DONE**)
5. Implement Routing Logic and Tools Based on User Query (**DONE**)
6. Add Chat History Management (**DONE**)
7. Integrate LangSmith Tracing (Come back when finish all first 19 steps)
8. Update Streamlit UI (Continuous improvement)
9. Form Input/Output Storing Structure in Markdown Format for Qdrant (**DONE**)
10. Convert LangChain to LangGraph
    10.1.0. Implement State Management (**DONE**)
    10.1.1. Add Configuration - Threading (**DONE**)
    10.1.2. Initialize Persistence and Checkpointer (**DONE**)
    10.1.3. Save All States to Postgres - Support time travel
    10.1.4. Initial double retrieval - Qdrant and Neo4j, they connect through some type of ID (Don't understand this at all)
    10.1.5. Reinforce Other Logic Workflows After This Step
10.2. Expression Logic - Durable Execution Engine and Structure
11. Enhance Routing Logic
    11.0. Evaluation Process - RAGAS
    11.1. Add Reflection/Self-Ask with LangGraph Time-Travel
    11.2. Tool Usage
    11.3. Planning + Action + Observation → Final Answer
12. Add Human-in-the-Loop (HITL) in SQL query (**DONE**)
13. Add Streaming Responses
14. Add Caching with Redis
15. Compile into a Single Main.py File (**DONE**)
16. Explore Multi-Agent System
17. Deployment
    17.1. Dockerize the Application
    17.2. Deploy on Cloud (AWS / GCP / Azure)
    17.3. Implement API Endpoints - FastAPI
18. Testing & Optimization
    18.1. Unit Testing
    18.2. Performance Optimization
19. Documentation & Tutorials - README
    19.1. User Guide
    19.2. Developer Guide

**NOTE**:
- Need to use /app/backend/utils/log.py code to logging
- All the code always in production ready state
- Manage codebase in modular structure (OOP where applicable)
- Write proper docstrings + comment for all functions and classes
- Typing must use for LangGraph State; Pydantic is a must for: Input, Output, Configs, etc.
- Follow best practices for security, error handling, and code quality

**NOTE (Status Reasons for Not Done / Half Finish)**:
- 4.2.4 OCR for Images/Scanned PDFs: Partial (external OCR for scanned PDFs only; no image OCR pipeline).
- 4.1.4 Resolve Connection Issues: Not verifiable (no dedicated fixes or docs found).
- 7 LangSmith Tracing: Not done (telemetry modules exist but empty; no wiring).
- 8 Streamlit UI (Continuous improvement): Ongoing (UI exists; no continuous improvement backlog or criteria).
- 10 Convert LangChain to LangGraph: Partial (LangGraph workflow exists but still uses LangChain agent inside).
- 10.1.3 Save All States to Postgres - Support time travel: Partial (LangGraph checkpointer stores state; no explicit time-travel API in app).
- 10.1.4 Double retrieval (Qdrant + Neo4j): Not done (Neo4j tool stub exists; no integration path).
- 10.1.5 Reinforce Other Logic Workflows After This Step: Not verifiable (no explicit milestone).
- 10.2 Durable Execution Engine: Not done (no durable execution subsystem beyond LangGraph checkpoints).
- 11 Enhance Routing Logic: Partial (basic routing exists; evaluation/reflection/planning incomplete).
- 11.0 RAGAS Evaluation: Not done (no RAGAS integration found).
- 11.1 Reflection/Self-Ask with Time-Travel: Partial (reflection exists; time-travel not wired).
- 11.2 Tool Usage: Not done (ToolUsage model/repo exists but no logging integration).
- 11.3 Planning + Action + Observation: Partial (planner exists; full agent loop not formalized).
- 13 Streaming Responses: Not done (no streaming in UI or workflow).
- 14 Caching with Redis: Not done (no Redis integration).
- 16 Multi-Agent System: Not done (single-agent workflow only).
- 17 Deployment: Not done (no Docker/Cloud/FastAPI scaffolding).
- 18 Testing & Optimization: Not done (no test suite or perf pipeline).
- 19 Documentation & Tutorials: Not done (README/Guides not fully written).