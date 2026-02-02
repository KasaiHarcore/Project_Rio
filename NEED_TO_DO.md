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
    4.7. Implement SQL Chat mode
        4.7.1. Schema transfering to LLM - Table name only - DBCopilot
        4.7.2. READ - WRITE separation
5. Integrate Qdrant Vector Store (**DONE**)
    5.1. Create HyDE and Query Rewriting (**DONE**)
    5.2. Add Sparse Embeddings and Hybrid Search (**DONE**)
    5.3. Add Cohere Reranker (**DONE**)
    5.4. Add OCR for Images and Scanned PDFs (Change to Image understanding -> Text information and save like other)
    5.5. Implement Web Search with Tavily (**DONE**)
6. Add Chat History Management
    6.1. Implement Long-term memory method - PostGreSQL (**DONE**)
    6.2. Implement Short-term memory method - Redis (**DONE**)
    6.3. Control memory existed time (Need to test)
    6.4. Re-order requested from system to database (Recent = Redis, Old = PostGre)
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
    12.2. Intergrate RAGAS for Evalute (Need test) 
14. Add Human-in-the-Loop (HITL)
    14.1. Allow / Not allow tool call request like Copilot on SQL 
    14.1.1. Enable to edit tool call request and applied on SQL
    14.1.2. Planning Step - effect the LLM action (**DONE**)
    14.1.3. Reflection + Verify -> Return Information -> Finalize (**DONE**)
15. Add Streaming Responses (**Done**)
14. Add Caching with Redis
    14.1. LLM generate title
    14.2. Graph State saving
15. Add Neo4j beside Qdrant for extracting information
16. Explore Multi-Agent System (**DONE**)
17. Deployment
    17.1. Dockerize the Application
    17.2. Deploy on Cloud (AWS / GCP / Azure)
    17.3. Implement REST API Endpoints - FastAPI
        17.3.1. Handle cut-off request
    17.4. New UI with React
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