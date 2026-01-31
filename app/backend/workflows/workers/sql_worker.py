"""
SQL Worker - Queries the application database.

The SQL Worker specializes in querying the PostgreSQL database
for structured data about users, threads, messages, and system state.

Responsibilities:
- Analyze questions to determine SQL queries needed
- Execute safe, read-only queries
- Format results for human consumption
- Protect sensitive data
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from backend.workflows.state import (
    AgentState,
    WorkerResult,
    WorkerType,
)
from backend.workflows.workers.base import BaseWorker
from backend.services.tools.sql_tool import sql_tool
from backend.utils.log import log_info, log_debug, log_warning


SQL_SYSTEM_PROMPT = """You are a SQL Query Assistant that helps retrieve information from the application database.

Available Tables:
- user: User accounts (id, email, full_name, created_at, is_active, is_superuser)
- thread: Conversation threads (id, user_id, title, mode, created_at, updated_at)
- message: Chat messages (id, thread_id, role, content, created_at)
- run: Agent execution runs (id, thread_id, mode, model_name, status, started_at, ended_at)
- run_steps: Execution steps within runs (id, run_id, step_type, name, status)
- tool_usage: Tool usage logs (id, thread_id, tool_name, input_data, output_data)
- audit_log: System audit logs (id, action, user_id, timestamp)

Guidelines:
- Only use SELECT statements (no modifications allowed)
- Be mindful of data sensitivity
- Format results clearly for the user
- If you're unsure about the schema, describe the schema first
- Limit results to avoid overwhelming the user

SQL Best Practices:
- Use JOINs appropriately
- Add WHERE clauses to filter relevant data
- Use ORDER BY for meaningful ordering
- LIMIT results (default max 100)
"""


class SQLWorker(BaseWorker):
    """
    SQL Worker queries the application database.
    
    Executes safe, read-only SQL queries to retrieve
    structured data from the PostgreSQL database.
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.SQL
    
    @property
    def name(self) -> str:
        return "SQL Query Worker"
    
    @property
    def description(self) -> str:
        return "Queries the application database for structured data"
    
    @property
    def system_prompt(self) -> str:
        return SQL_SYSTEM_PROMPT
    
    def __init__(self, config=None, max_rows: int = 100):
        """
        Initialize the SQL Worker.
        
        Args:
            config: Optional agent configuration
            max_rows: Maximum rows to return per query
        """
        super().__init__(config=config)
        self.max_rows = max_rows
    
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Analyze the question and execute appropriate SQL queries.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult containing query results
        
        Raises:
            PermissionError: If user is not an admin
        """
        # ===== SECURITY CHECK: Admin only =====
        metadata = state.get("metadata", {})
        user_role = metadata.get("user_role", "user")
        
        if user_role != "admin":
            log_warning(f"SQL Worker blocked: unauthorized access attempt (role={user_role})")
            return WorkerResult(
                worker_type=WorkerType.SQL,
                success=False,
                content="**Access Denied**: SQL mode is restricted to administrators only.",
                error="Unauthorized: Admin role required for SQL queries"
            )
        # ===== END SECURITY CHECK =====
        
        question = self.get_question(state)
        
        log_info(f"SQL Worker analyzing: {question[:100]}...")
        
        # First, determine what SQL query to run
        query_plan = self._plan_query(question, state)
        
        if query_plan.get("needs_schema"):
            # User is asking about the database structure
            return self._describe_schema()
        
        if query_plan.get("query"):
            # Execute the planned query
            return self._execute_query(query_plan["query"], query_plan.get("explanation", ""))
        
        # Generate a query using LLM
        return self._generate_and_execute_query(question, state)
    
    def _plan_query(self, question: str, state: AgentState) -> Dict[str, Any]:
        """
        Analyze the question to determine the query approach.
        
        Args:
            question: User's question
            state: Current state
        
        Returns:
            Query plan dictionary
        """
        question_lower = question.lower()
        
        # Check for schema/structure questions
        schema_keywords = ["schema", "tables", "structure", "columns", "what tables"]
        if any(kw in question_lower for kw in schema_keywords):
            return {"needs_schema": True}
        
        # Check for specific table queries
        table_keywords = {
            "user": ["user", "account", "member"],
            "thread": ["thread", "conversation", "chat"],
            "message": ["message", "chat history"],
            "run": ["run", "execution", "agent run"],
            "tool_usage": ["tool", "tool usage"],
        }
        
        # Simple pattern matching for common queries
        if "how many" in question_lower:
            for table, keywords in table_keywords.items():
                if any(kw in question_lower for kw in keywords):
                    return {
                        "query": f"SELECT COUNT(*) as count FROM {table}",
                        "explanation": f"Counting {table} records",
                    }
        
        if "recent" in question_lower or "latest" in question_lower:
            for table, keywords in table_keywords.items():
                if any(kw in question_lower for kw in keywords):
                    return {
                        "query": f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 10",
                        "explanation": f"Getting latest {table} records",
                    }
        
        return {}
    
    def _describe_schema(self) -> WorkerResult:
        """
        Return database schema description.
        
        Returns:
            WorkerResult with schema information
        """
        try:
            # Get schema description
            schema_desc = sql_tool.describe_schema()
            
            # Also get table list
            table_info = sql_tool.get_table_info()
            
            content = "## Database Schema\n\n"
            content += schema_desc.replace("\\n", "\n")
            
            if table_info.get("success") and table_info.get("tables"):
                content += f"\n\n**Available Tables:** {', '.join(table_info['tables'])}"
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=content,
                metadata={"type": "schema"},
            )
            
        except Exception as e:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=str(e),
            )
    
    def _execute_query(self, query: str, explanation: str = "") -> WorkerResult:
        """
        Execute a SQL query and return formatted results.
        
        Args:
            query: SQL query to execute
            explanation: Human-readable explanation
        
        Returns:
            WorkerResult with query results
        """
        log_info(f"Executing SQL: {query}")
        
        try:
            result = sql_tool.execute_query(query)
            
            if not result.get("success"):
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=False,
                    content=f"Query failed: {result.get('error', 'Unknown error')}",
                    error=result.get("error"),
                    metadata={"query": query},
                )
            
            # Format the results
            formatted = self._format_results(result, explanation)
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=formatted,
                metadata={
                    "query": query,
                    "row_count": result.get("row_count", 0),
                    "columns": result.get("columns", []),
                },
            )
            
        except Exception as e:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=str(e),
                metadata={"query": query},
            )
    
    def _generate_and_execute_query(
        self,
        question: str,
        state: AgentState,
    ) -> WorkerResult:
        """
        Use LLM to generate and execute a SQL query.
        
        Args:
            question: User's question
            state: Current state
        
        Returns:
            WorkerResult with query results
        """
        # Get schema for context
        schema_info = sql_tool.describe_schema()
        
        prompt = f"""Given the following database schema:

{schema_info}

Generate a SQL query to answer this question: {question}

Rules:
- Only use SELECT statements
- Limit results to 100 rows maximum
- Include relevant columns only
- Use appropriate JOINs if needed

Respond with ONLY the SQL query, no explanations.
"""
        
        try:
            generated_query = self._call_llm(user_prompt=prompt)
            
            # Clean up the query
            query = generated_query.strip()
            
            # Remove markdown code blocks if present
            if query.startswith("```"):
                lines = query.split("\n")
                query = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                )
            
            # Validate it's a SELECT query
            if not query.upper().strip().startswith("SELECT"):
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=False,
                    content="Generated query is not a SELECT statement",
                    error="Only SELECT queries are allowed",
                )
            
            # Execute the generated query
            return self._execute_query(
                query,
                explanation=f"Query generated for: {question}",
            )
            
        except Exception as e:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Failed to generate/execute query: {str(e)}",
            )
    
    def _format_results(
        self,
        result: Dict[str, Any],
        explanation: str = "",
    ) -> str:
        """
        Format SQL query results for presentation.
        
        Args:
            result: Query result dictionary
            explanation: Optional explanation
        
        Returns:
            Formatted results string
        """
        parts = ["## SQL Query Results\n"]
        
        if explanation:
            parts.append(f"*{explanation}*\n")
        
        row_count = result.get("row_count", 0)
        parts.append(f"**Returned {row_count} row(s)**\n")
        
        data = result.get("data", [])
        columns = result.get("columns", [])
        
        if not data:
            parts.append("\n*No data returned*")
            return "\n".join(parts)
        
        # Create a simple table
        if columns:
            # Header
            parts.append("\n| " + " | ".join(columns) + " |")
            parts.append("| " + " | ".join(["---"] * len(columns)) + " |")
            
            # Rows (limit to 20 for display)
            for row in data[:20]:
                values = [str(row.get(col, ""))[:50] for col in columns]
                parts.append("| " + " | ".join(values) + " |")
            
            if len(data) > 20:
                parts.append(f"\n*... and {len(data) - 20} more rows*")
        
        return "\n".join(parts)
    
    def execute_direct(self, query: str) -> WorkerResult:
        """
        Execute a SQL query directly (for programmatic use).
        
        Args:
            query: SQL query to execute
        
        Returns:
            WorkerResult with query results
        """
        return self._execute_query(query)


def create_sql_worker(config=None, max_rows: int = 100) -> SQLWorker:
    """Factory function to create a SQLWorker."""
    return SQLWorker(config=config, max_rows=max_rows)
