"""
SQL Worker - Queries the application database with HITL approval workflow.

The SQL Worker specializes in querying the PostgreSQL database
for structured data about users, threads, messages, and system state.

Human-in-the-Loop (HITL) Features:
- Schema-aware SQL generation (DBCopilot approach)
- Automatic operation classification (READ/WRITE/DELETE/ADMIN)
- LangGraph interrupt() for approval workflow
- User can approve, edit, or reject SQL before execution
- Re-classification of user-edited SQL for safety
- Safe execution with admin-only restrictions

Approval Workflow:
1. SQL is generated based on user question
2. Operation is classified by danger level
3. If approval required: interrupt() pauses execution
4. User chooses: approve / edit / reject
5. If approved or edited: execute SQL
6. Return formatted results

Responsibilities:
- Analyze questions with schema context
- Generate appropriate SQL queries
- Classify SQL operations by danger level
- Request approval for WRITE/dangerous operations via interrupt()
- Handle user edits with re-classification
- Execute safe/approved queries
- Format results for human consumption
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional

from langgraph.types import interrupt

from utils.timezone import utc_now

from workflows.state import (
    AgentState,
    HumanInterrupt,
    HumanInterruptType,
    WorkerResult,
    WorkerType,
)
from workflows.workers.base import BaseWorker
from infrastructure.tools.sql_tool import sql_tool
from services.sql_schema_service import sql_schema_service
from infrastructure.db.sql_classifier import (
    sql_classifier,
    SQLClassification,
    SQLOperationType,
    DangerLevel,
    ApprovalPolicy,
)
from schemas.sql_approval import (
    SQLApprovalRequest,
    SQLApprovalStatus,
    PendingSQLApproval,
)
from utils.log import log_info, log_debug, log_warning, log_error, log_success


SQL_SYSTEM_PROMPT = """I am the SQL module. I help Sensei query and manage the application database safely.

Guidelines:
- I generate appropriate SQL statements based on Sensei's intent.
- I am mindful of data sensitivity.
- I format results clearly and concisely.
- If unsure about the schema, I describe what's available first.
- For READ operations (SELECT): I limit results to avoid overwhelming output.
- For WRITE operations (INSERT/UPDATE/DELETE): Sensei's approval is required.

SQL Best Practices:
- Use JOINs appropriately
- Add WHERE clauses to filter relevant data
- Use ORDER BY for meaningful ordering
- LIMIT results (default max 100 for SELECT)
- Always include specific conditions for UPDATE/DELETE operations
"""


# Default approval timeout in minutes
SQL_APPROVAL_TIMEOUT_MINUTES = 30


class SQLWorker(BaseWorker):
    """
    SQL Worker queries the application database with HITL support.
    
    Executes SQL queries with intelligent operation classification
    and human-in-the-loop approval for dangerous operations.
    
    Flow:
    1. Get schema context for LLM
    2. Generate SQL based on user question
    3. Classify operation type and danger level
    4. For READ/safe operations: execute immediately
    5. For WRITE/dangerous operations: request approval via interrupt
    6. After approval: execute and return results
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.SQL
    
    @property
    def name(self) -> str:
        return "SQL Query Worker"
    
    @property
    def description(self) -> str:
        return "Queries and modifies the application database with approval workflow"
    
    @property
    def system_prompt(self) -> str:
        return SQL_SYSTEM_PROMPT

    def _build_system_prompt(self, schema_context: str) -> str:
        """Build the full system prompt with live schema injected."""
        base = self.system_prompt
        if schema_context:
            # Insert the schema block right after the first line
            return f"{base}\n{schema_context}\n"
        return base
    
    def __init__(self, config=None, max_rows: int = 100):
        """
        Initialize the SQL Worker.
        
        Args:
            config: Optional agent configuration
            max_rows: Maximum rows to return per query
        """
        super().__init__(config=config)
        self.max_rows = max_rows
    
    def _get_schema_context(self, state: AgentState) -> str:
        """Get schema context, using cache if available."""
        cached = state.get("sql_schema_context")
        if cached:
            return cached
        
        try:
            # Use schema service to get LLM-optimized context
            question = self.get_question(state)
            relevant_tables = sql_schema_service.infer_relevant_tables(question)
            return sql_schema_service.get_llm_context(
                relevant_tables=relevant_tables,
                include_relationships=True,
                max_tables=10,
            )
        except Exception as e:
            log_warning(f"Failed to get schema context: {e}")
            # Fallback to basic schema
            return sql_tool.describe_schema()
    
    def _create_approval_request(
        self,
        sql: str,
        natural_query: str,
        classification: SQLClassification,
        explanation: str,
        state: AgentState,
    ) -> SQLApprovalRequest:
        """Create an approval request for a SQL operation."""
        return SQLApprovalRequest(
            request_id=str(uuid.uuid4()),
            thread_id=state.get("thread_id", ""),
            run_id=state.get("metadata", {}).get("run_id"),
            generated_sql=sql,
            natural_language_query=natural_query,
            operation_type=classification.operation_type,
            danger_level=classification.danger_level,
            affected_tables=classification.affected_tables,
            estimated_rows_affected=classification.estimated_rows_affected,
            approval_policy=classification.approval_policy,
            warnings=classification.warnings,
            expires_at=utc_now() + timedelta(minutes=SQL_APPROVAL_TIMEOUT_MINUTES),
            explanation=explanation,
        )
    
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Analyze the question and execute appropriate SQL queries.
        
        With LangGraph interrupt(), the approval flow is handled automatically:
        1. If SQL needs approval, interrupt() pauses execution
        2. Graph waits for user to approve/edit/reject
        3. When resumed, execution continues with the user's decision
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult containing query results
        """
        question = self.get_question(state)
        log_info(f"SQL Worker analyzing: {question[:100]}...")
        
        # Get schema context
        schema_context = self._get_schema_context(state)
        
        # First, determine what SQL query to run
        query_plan = self._plan_query(question, state, schema_context)
        
        if query_plan.get("needs_schema"):
            # User is asking about the database structure
            return self._describe_schema()
        
        if query_plan.get("query"):
            # Execute the planned query with classification
            return self._classify_and_execute(
                query=query_plan["query"],
                explanation=query_plan.get("explanation", ""),
                natural_query=question,
                state=state,
            )
        
        # Generate a query using LLM
        return self._generate_and_execute_query(question, state, schema_context)
    
    def _classify_and_execute(
        self,
        query: str,
        explanation: str,
        natural_query: str,
        state: AgentState,
    ) -> WorkerResult:
        """
        Classify the query and execute or request approval.
        
        Args:
            query: SQL query to execute
            explanation: Human-readable explanation
            natural_query: Original natural language query
            state: Current state
        
        Returns:
            WorkerResult with results or approval request
        """
        # Classify the operation
        classification = sql_classifier.classify(query)
        
        log_debug(
            f"SQL classified: {classification.operation_type.value}, "
            f"danger={classification.danger_level.value}"
        )
        
        # Check if approval is required
        if classification.approval_policy.requires_approval:
            return self._request_approval(
                sql=query,
                natural_query=natural_query,
                classification=classification,
                explanation=explanation,
                state=state,
            )
        
        # Safe operation - execute immediately
        return self._execute_query(query, explanation)
    
    # Maximum auto-retry attempts when SQL execution fails
    MAX_AUTO_RETRIES = 3

    def _request_approval(
        self,
        sql: str,
        natural_query: str,
        classification: SQLClassification,
        explanation: str,
        state: AgentState,
    ) -> WorkerResult:
        """
        Request user approval for a SQL operation using LangGraph interrupt().

        Supports:
        - Approve: Execute SQL as-is
        - Edit: Modify SQL before execution
        - Reject: Cancel the operation
        - Auto-approve: Skip interrupt when ``sql_auto_approve`` is set in thread metadata
        - Auto-retry: If execution fails, ask LLM to fix the query (up to 3 retries)

        Returns:
            WorkerResult with execution results or error
        """
        # Check admin requirement for critical operations
        metadata = state.get("metadata", {})
        user_role = metadata.get("user_role", "user")

        if classification.approval_policy == ApprovalPolicy.ADMIN_ONLY and user_role != "admin":
            log_warning(f"SQL Worker blocked: admin-only operation (role={user_role})")
            return WorkerResult(
                worker_type=WorkerType.SQL,
                success=False,
                content=f"**Access Denied**: This operation ({classification.operation_type.value}) requires administrator privileges.",
                error="Unauthorized: Admin role required for this SQL operation",
                metadata={"classification": classification.to_summary()},
            )

        # ── Auto-approve check ─────────────────────────────────
        # If the user previously chose "always approve" for this thread,
        # skip the interrupt and proceed directly.
        if metadata.get("sql_auto_approve"):
            log_info("SQL auto-approve enabled for this thread — skipping interrupt")
            result = self._execute_with_retry(sql, explanation, natural_query, state)
            if result.metadata is None:
                result.metadata = {}
            result.metadata["approval_status"] = "auto_approved"
            return result

        # Create approval request
        approval_request = self._create_approval_request(
            sql=sql,
            natural_query=natural_query,
            classification=classification,
            explanation=explanation,
            state=state,
        )

        log_info(f"SQL approval requested: {approval_request.request_id}")

        # Pause execution and wait for user response using interrupt()
        response = interrupt({
            "type": "sql_approval",
            "request_id": approval_request.request_id,
            "message": approval_request.to_user_message(),
            "sql": sql,
            "natural_query": natural_query,
            "operation_type": classification.operation_type.value,
            "danger_level": classification.danger_level.value,
            "affected_tables": classification.affected_tables,
            "estimated_rows_affected": classification.estimated_rows_affected,
            "warnings": classification.warnings,
            "explanation": explanation,
        })

        # When resumed, response contains user's decision
        log_info(f"SQL approval response received: {response}")

        action = response.get("action", "reject") if isinstance(response, dict) else "reject"

        if action == "reject":
            reason = response.get("reason", "User rejected the operation") if isinstance(response, dict) else "User rejected the operation"
            log_warning(f"SQL operation rejected: {reason}")
            return WorkerResult(
                worker_type=WorkerType.SQL,
                success=False,
                content=f"**Operation Cancelled**\n\n{reason}",
                error="Operation rejected by user",
                metadata={"approval_status": "rejected", "reason": reason},
            )

        # Determine which SQL to execute
        sql_to_execute = sql
        was_modified = False

        if action == "edit" and isinstance(response, dict) and response.get("modified_sql"):
            sql_to_execute = response["modified_sql"].strip()
            was_modified = True
            log_info(f"User modified SQL: {sql_to_execute[:100]}...")

            # Re-classify the modified SQL for safety
            new_classification = sql_classifier.classify(sql_to_execute)
            log_info(
                f"Modified SQL classification: {new_classification.operation_type.value}, "
                f"danger={new_classification.danger_level.value}"
            )

            # If modified SQL is more dangerous, interrupt again for re-approval
            if new_classification.danger_level.value > classification.danger_level.value:
                log_warning(
                    f"Modified SQL has higher danger level: "
                    f"{new_classification.danger_level.value} > {classification.danger_level.value}"
                )
                return self._request_approval(
                    sql=sql_to_execute,
                    natural_query=natural_query,
                    classification=new_classification,
                    explanation=f"Re-approval needed — modified query is more dangerous: {natural_query}",
                    state=state,
                )

            explanation = f"Modified query: {natural_query}"

        # Execute with auto-retry support
        log_success(f"Executing {'modified' if was_modified else 'approved'} SQL: {sql_to_execute[:100]}...")
        result = self._execute_with_retry(sql_to_execute, explanation, natural_query, state)

        # Add approval metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata.update({
            "approval_status": "approved",
            "was_modified": was_modified,
            "original_sql": sql if was_modified else None,
            "request_id": approval_request.request_id,
        })

        return result

    def _execute_with_retry(
        self,
        sql: str,
        explanation: str,
        natural_query: str,
        state: AgentState,
        retry_count: int = 0,
    ) -> WorkerResult:
        """
        Execute SQL with auto-retry on failure.

        If execution fails, asks the LLM to fix the query and retries
        (up to MAX_AUTO_RETRIES times). If the fixed query is more
        dangerous, it interrupts for re-approval instead of auto-executing.

        Args:
            sql: SQL query to execute
            explanation: Human-readable explanation
            natural_query: Original natural language query
            state: Current agent state
            retry_count: Current retry attempt number

        Returns:
            WorkerResult with execution results
        """
        result = self._execute_query(sql, explanation)

        if result.success or retry_count >= self.MAX_AUTO_RETRIES:
            if not result.success and retry_count >= self.MAX_AUTO_RETRIES:
                log_warning(f"SQL execution failed after {retry_count} retries — giving up")
                result.content += (
                    f"\n\n**Auto-fix exhausted** ({retry_count} retries).\n"
                    "You may need to manually adjust the query and try again."
                )
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["needs_manual_help"] = True
                result.metadata["retry_count"] = retry_count
            return result

        # Auto-retry: ask LLM to fix the failed query
        error_msg = result.error or "Unknown error"
        log_info(f"SQL execution failed (attempt {retry_count + 1}), asking LLM to fix: {error_msg[:200]}")

        schema_context = self._get_schema_context(state)
        fix_prompt = (
            f"The following SQL query failed with an error. Fix it.\n\n"
            f"Original question: {natural_query}\n\n"
            f"Failed SQL:\n```sql\n{sql}\n```\n\n"
            f"Error: {error_msg}\n\n"
            f"Use the database schema provided in the system instructions.\n"
            f"Return ONLY the corrected SQL query, no explanations."
        )

        try:
            fixed_sql = self._call_llm(
                user_prompt=fix_prompt,
                system_prompt=self._build_system_prompt(schema_context),
            ).strip()

            # Remove markdown code blocks if present
            if fixed_sql.startswith("```"):
                lines = fixed_sql.split("\n")
                fixed_sql = "\n".join(
                    line for line in lines if not line.startswith("```")
                )

            if not fixed_sql or fixed_sql == sql:
                log_warning("LLM returned empty or identical SQL — stopping retry")
                return result

            # Re-classify for safety
            original_classification = sql_classifier.classify(sql)
            new_classification = sql_classifier.classify(fixed_sql)

            # If the fix is more dangerous, interrupt for re-approval
            if new_classification.danger_level.value > original_classification.danger_level.value:
                log_warning("Fixed SQL is more dangerous — requesting re-approval")
                return self._request_approval(
                    sql=fixed_sql,
                    natural_query=natural_query,
                    classification=new_classification,
                    explanation=f"Auto-fixed query (attempt {retry_count + 1}) — higher danger level, needs re-approval",
                    state=state,
                )

            log_info(f"Retrying with fixed SQL (attempt {retry_count + 1}): {fixed_sql[:100]}...")
            return self._execute_with_retry(
                sql=fixed_sql,
                explanation=f"Auto-fixed query (attempt {retry_count + 1}): {natural_query}",
                natural_query=natural_query,
                state=state,
                retry_count=retry_count + 1,
            )

        except Exception as fix_err:
            log_error(f"LLM fix attempt failed: {fix_err}")
            return result
    

    
    def _plan_query(self, question: str, state: AgentState, schema_context: str = "") -> Dict[str, Any]:
        """
        Analyze the question to determine the query approach.
        
        Args:
            question: User's question
            state: Current state
            schema_context: Schema context for LLM
        
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
        schema_context: str = "",
    ) -> WorkerResult:
        """
        Use LLM to generate and execute a SQL query.
        
        Args:
            question: User's question
            state: Current state
            schema_context: Schema context for LLM
        
        Returns:
            WorkerResult with query results or approval request
        """
        # Get schema for context if not provided
        if not schema_context:
            schema_context = self._get_schema_context(state)

        prompt = f"""Generate a SQL query to answer this question: {question}

Rules:
- Generate appropriate SQL (SELECT, INSERT, UPDATE, DELETE as needed)
- For SELECT: Limit results to 100 rows maximum
- For INSERT/UPDATE/DELETE: Be precise with conditions
- Include relevant columns only
- Use appropriate JOINs if needed
- Use the database schema provided in the system instructions

Respond with ONLY the SQL query, no explanations.
"""

        try:
            generated_query = self._call_llm(
                user_prompt=prompt,
                system_prompt=self._build_system_prompt(schema_context),
            )
            
            # Clean up the query
            query = generated_query.strip()
            
            # Remove markdown code blocks if present
            if query.startswith("```"):
                lines = query.split("\n")
                query = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                )
            
            # Classify and execute (with approval if needed)
            return self._classify_and_execute(
                query=query,
                explanation=f"Query generated for: {question}",
                natural_query=question,
                state=state,
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
