"""ReAct tools for SQL database access with human-in-the-loop approval.

Wraps SQLTool for reads and adds HITL approval for write operations
via LangGraph's interrupt() mechanism.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

from infrastructure.tools.sql_tool import sql_tool
from infrastructure.db.sql_classifier import SQLClassifier, DangerLevel, ApprovalPolicy
from utils.log import log_info, log_warning

_classifier = SQLClassifier()


def build_sql_tools(user_id: str) -> list:
    """Build SQL tools (admin-only). Only call this for admin users."""

    @tool
    def describe_database_schema() -> str:
        """Get a description of the database schema including tables, columns, and relationships.

        Use this BEFORE writing SQL queries to understand the database structure.

        Returns:
            Natural language description of the database schema.
        """
        return sql_tool.describe_schema()

    @tool
    def get_table_info(table_name: Optional[str] = None) -> str:
        """Get detailed info about a specific table or all tables.

        Args:
            table_name: Table name for detailed info. Omit for overview of all tables.

        Returns:
            JSON with columns, primary keys, foreign keys, and indexes.
        """
        result = sql_tool.get_table_info(table_name)
        return json.dumps(result, default=str)

    @tool
    def execute_sql(query: str, explanation: str = "") -> str:
        """Execute a SQL query against the database.

        Read queries (SELECT) execute immediately.
        Write queries (INSERT, UPDATE, DELETE) require user approval first.

        Args:
            query: The SQL query to execute.
            explanation: Brief explanation of what this query does and why.

        Returns:
            JSON with query results (columns, data, row_count) or error message.
            For write operations, may pause for user approval.
        """
        classification = _classifier.classify(query)

        needs_approval = classification.approval_policy not in (
            ApprovalPolicy.AUTO,
            ApprovalPolicy.NOTIFY,
        )

        if needs_approval:
            response = interrupt({
                "type": "sql_approval",
                "sql": query,
                "explanation": explanation,
                "operation_type": classification.operation_type.value,
                "danger_level": classification.danger_level.value,
                "affected_tables": classification.affected_tables,
                "estimated_rows_affected": classification.estimated_rows_affected,
                "warnings": classification.warnings or [],
                "approval_policy": classification.approval_policy.value,
            })

            action = response.get("action", "reject") if isinstance(response, dict) else "reject"

            if action == "reject":
                return json.dumps({
                    "status": "rejected",
                    "message": "SQL operation was rejected by the user.",
                })

            if action == "edit":
                edited_sql = response.get("edited_sql", query)
                if edited_sql != query:
                    new_classification = _classifier.classify(edited_sql)
                    if new_classification.danger_level.value > classification.danger_level.value:
                        return json.dumps({
                            "status": "rejected",
                            "message": "Edited SQL is more dangerous than the original. Rejected for safety.",
                        })
                    query = edited_sql

        result = sql_tool.execute_query(query)
        return json.dumps(result, default=str)

    return [describe_database_schema, get_table_info, execute_sql]
