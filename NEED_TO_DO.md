Dev Route: (AGILE)
1. Establish Basic Foundation (**DONE**)
2. Integrate Streamlit (**DONE**)
3. Complete Basic RAG System Based on PDF Extraction (**DONE**)
4. Develop Advanced RAG Features (**DONE**)
    4.1. Add SQL Database - PostgreSQL via SQLAlchemy (**DONE**)
    4.2. Implement CRUD Operations with Full Case Handling (**DONE**)
    4.3. Add Read/Retrieve Operations (**DONE**)
    4.4. Integrate Alembic (**DONE**)
    4.5. Resolve Connection Issues (**DONE**)
    4.6. Format Input/Output with Pydantic (**DONE**)
    4.7. Implement SQL Chat mode (**DONE**)
        4.7.1. Schema transfering to LLM - Table name only - DBCopilot (**DONE**)
        4.7.2. READ - WRITE separation (**DONE**)
5. Integrate Qdrant Vector Store (**DONE**)
    5.1. Create HyDE and Query Rewriting (**DONE**)
    5.2. Add Sparse Embeddings and Hybrid Search (**DONE**)
    5.3. Add Cohere Reranker (**DONE**)
    5.4. Add OCR for Images and Scanned PDFs (Change to Image understanding -> Text information and save like other)
    5.5. Implement Web Search with Tavily (**DONE**)
6. Add Chat History Management
    6.1. Implement Long-term memory method - PostGreSQL (**DONE**)
    6.2. Implement Short-term memory method - Redis (**DONE**)
    6.3. Control memory existed time (Simple test pass, need long conversation test)
    6.4. Re-order requested from system to database (**DONE**)
7. Update Streamlit UI (Continuous improvement)
8. Form Input/Output Storing Structure in Markdown Format for Qdrant (**DONE**)
9. Convert LangChain to LangGraph (**DONE**)
    9.1. Implement State Management (**DONE**)
    9.2. Add Configuration - Threading (**DONE**)
    9.3. Initialize Persistence and Checkpointer (**DONE**)
11. Durable Execution Engine and Structure (**DONE**)
    11.1. Apply durability = "sync" in graph stream (**DONE**)
12. Evaluation
    12.1. Intergrate LangSmith for Tracing (**DONE**)
    12.2. Intergrate RAGAS for Evalute (**DONE**)
14. Add Human-in-the-Loop (HITL)
    14.1. Allow / Not allow tool call request like Copilot on SQL (Need test) 
    14.1.1. Enable to edit tool call request and applied on SQL (Need test) 
    14.1.2. Planning Step - effect the LLM action (**DONE**)
    14.1.3. Reflection + Verify -> Return Information -> Finalize (**DONE**)
15. Add Streaming Responses (**Done**)
14. Add Caching with Redis (**Done**)
15. Add Neo4j beside Qdrant for extracting information
16. Explore Multi-Agent System (**DONE**)
17. Deployment
    17.1. Dockerize the Application
    17.2. Deploy on Cloud (AWS / GCP / Azure)
    17.3. Implement REST API Endpoints - FastAPI
        17.3.1. Handle cut-off request (Need test)
    17.4. New UI with React
        17.4.0. Test all MVP worker - RAG, SQL, Web Search (**DONE**)
        17.4.1. Fix Note worker - re-mapping quicknote instead of raw output to webpage render (Need test)
        17.4.2. Fix Workspace - Cannot add file into this
        17.4.3. Test Planning worker (Need test)
        17.4.4. Separate Planning / Arona completely in Operation page (**Done**)
        17.4.5. Agent response line by line - mimic human response; Be able to send sticker (Half finish)
        17.4.6. Complete Artifact Page -> Map workspace at Operation page to this (**Done**)
        17.4.7. Map Mission page -> Upcoming Deadlinee at Office page (**Done**)
        17.4.8. Agent allowed to stored Session memory - Only existed in 1 chat session
        17.4.9. Fix agent name in chat (**Done**)
        17.4.10. Support IDE developed on web - mimic vscode.dev or Replit (If possible)
        17.4.11. Re-make autonomous coding agent (Like Copilot/Anti-Gravity/all product related)
            17.4.12. Project Ingestion
                - List all the project in the workspace
                - Read a subset of files
                - Chunk them
                - Can be summarize
            17.4.13. Planning
                - Make TODO list
                - Allow user to review / modification manual or auto
                - Mostly this part will used Engineering to control over AI behavior
            17.4.14. Execution
                - Making a Checklist
                - Complete each task one by one (Create -> Test -> Verify)
                - Allow user interrupt in the middle of the task
                - Summary what happend and what the result
18. Testing & Optimization
    18.1. Unit Testing
    18.2. Performance Optimization
19. Documentation & Tutorials - README
    19.1. User Guide
    19.2. Developer Guide
    19.3. API Reference (With proper used)

**NOTE**:
- Need to use /app/backend/utils/log.py code to logging
- All the code always in production ready state
- Manage codebase in modular structure (OOP where applicable)
- Write proper docstrings + comment for all functions and classes
- Typing must use for LangGraph State; Pydantic is a must for: Input, Output, Configs, etc.
- Follow best practices for security, error handling, and code quality