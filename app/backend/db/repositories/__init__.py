"""Repository Layer for Database CRUD and Queries.

Repositories encapsulate database access logic, providing:
- Clean separation between business logic and data access
- Consistent error handling with custom exceptions
- Typed methods with proper documentation

Usage:
    from backend.db import get_db, RunRepository
    
    def get_run_service(db: Session = Depends(get_db)):
        repo = RunRepository(db)
        run = repo.get_by_id("run-id")
        return run

Exception Handling:
    - DatabaseError: General database failures
    - NotFoundError: Resource not found
    - DuplicateError: Unique constraint violation
"""

from backend.db.repositories.run_repo import RunRepository
from backend.db.repositories.tool_usage_repo import ToolUsageRepository

__all__ = [
    "RunRepository",
    "ToolUsageRepository",
]
