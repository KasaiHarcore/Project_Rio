"""SQL tool for structured data store and retrieval."""

from __future__ import annotations

import os
import sqlalchemy
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional, Tuple
from infrastructure.dto.session import get_db_context, get_engine, init_db
from utils.log import log_info, log_error, log_debug, log_warning, log_success
from core.exceptions import DatabaseError, ValidationError


class SQLTool:
    """
    Designed for information retrieval from application database (users, threads,
    messages, configurations, tool usage, audit logs).
    """

    def __init__(
        self,
        max_rows: int = 1000,
        timeout: int = 30,
        allow_write: Optional[bool] = None,
    ):
        """Initialize SQL tool."""
        self.max_rows = max_rows
        self.timeout = timeout
        if allow_write is None:
            allow_write = os.getenv("SQL_ALLOW_WRITE", "False").lower() == "true"
        self.allow_write = allow_write
        self.engine = get_engine()
        log_debug(f"SQLTool initialized (max_rows={max_rows}, timeout={timeout})")

    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query and return results."""
        try:
            log_debug(f"Executing SQL query: {query[:100]}...")
            
            # Validate query
            self._validate_query(query)
            
            with get_db_context() as db:
                # Execute query with timeout
                result = db.execute(
                    text(query).execution_options(timeout=self.timeout),
                    params or {}
                )
                
                # Fetch results
                if result.returns_rows:
                    rows = result.fetchmany(self.max_rows)
                    columns = list(result.keys())
                    
                    # Convert to list of dictionaries
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    log_success(f"Query executed successfully, returned {len(data)} rows")
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "columns": columns,
                        "error": None,
                    }
                else:
                    # For non-SELECT queries (INSERT, UPDATE, DELETE)
                    db.commit()
                    row_count = result.rowcount
                    
                    log_success(f"Query executed successfully, affected {row_count} rows")
                    
                    return {
                        "success": True,
                        "data": [],
                        "row_count": row_count,
                        "columns": [],
                        "error": None,
                    }
                    
        except ValidationError:
            raise
        except (OperationalError, ProgrammingError) as e:
            error_msg = f"SQL execution error: {str(e)}"
            log_error(error_msg)
            return {
                "success": False,
                "data": [],
                "row_count": 0,
                "columns": [],
                "error": error_msg,
            }
        except SQLAlchemyError as e:
            error_msg = f"Database error: {str(e)}"
            log_error(error_msg)
            raise DatabaseError(error_msg)

    def get_table_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about database tables."""
        try:
            inspector = inspect(self.engine)
            
            if table_name:
                # Get specific table info
                log_debug(f"Getting info for table: {table_name}")
                
                if not inspector.has_table(table_name):
                    log_warning(f"Table not found: {table_name}")
                    return {
                        "success": False,
                        "error": f"Table '{table_name}' not found",
                    }
                
                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": columns,
                    "primary_key": pk_constraint,
                    "foreign_keys": foreign_keys,
                    "indexes": indexes,
                }
            else:
                # Get all tables
                log_debug("Getting info for all tables")
                table_names = inspector.get_table_names()
                
                tables_info = {}
                for tbl in table_names:
                    tables_info[tbl] = {
                        "columns": inspector.get_columns(tbl),
                        "primary_key": inspector.get_pk_constraint(tbl),
                        "foreign_keys": inspector.get_foreign_keys(tbl),
                    }
                
                log_success(f"Retrieved info for {len(table_names)} tables")
                
                return {
                    "success": True,
                    "tables": table_names,
                    "table_info": tables_info,
                }
                
        except SQLAlchemyError as e:
            error_msg = f"Error getting table info: {str(e)}"
            log_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

    def get_sample_data(
        self, 
        table_name: str, 
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get sample data from a table."""
        try:
            log_debug(f"Getting sample data from table: {table_name}")

            inspector = inspect(self.engine)
            if table_name not in inspector.get_table_names():
                raise ValidationError(f"Table '{table_name}' not found")
            
            query = f"SELECT * FROM {table_name} LIMIT :limit"
            result = self.execute_query(query, {"limit": min(limit, self.max_rows)})
            
            if result["success"]:
                log_success(f"Retrieved {result['row_count']} sample rows")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting sample data: {str(e)}"
            log_error(error_msg)
            return {
                "success": False,
                "data": [],
                "error": error_msg,
            }

    def describe_schema(self) -> str:
        """Generate a natural language description of the database schema.
        
        Returns:
            Formatted string describing the database schema
        """
        try:
            log_debug("Generating schema description")
            
            table_info = self.get_table_info()
            
            if not table_info["success"]:
                return f"Error: {table_info.get('error', 'Unknown error')}"
            
            description_parts = ["Database Schema for LangGraph Application:\\n"]
            description_parts.append("Tables: user, thread, message, configuration, tool_usage, audit_log\\n")
            
            for table_name in table_info["tables"]:
                info = table_info["table_info"][table_name]
                
                description_parts.append(f"\\nTable: {table_name}")
                description_parts.append("Columns:")
                
                for col in info["columns"]:
                    col_desc = f"  - {col['name']}: {col['type']}"
                    if not col.get("nullable", True):
                        col_desc += " (NOT NULL)"
                    if col.get("default") is not None:
                        col_desc += f" DEFAULT {col['default']}"
                    description_parts.append(col_desc)
                
                # Add primary key info
                if info["primary_key"] and info["primary_key"].get("constrained_columns"):
                    pk_cols = ", ".join(info["primary_key"]["constrained_columns"])
                    description_parts.append(f"  Primary Key: ({pk_cols})")
                
                # Add foreign key info
                if info["foreign_keys"]:
                    description_parts.append("  Foreign Keys:")
                    for fk in info["foreign_keys"]:
                        fk_desc = f"    - {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}"
                        description_parts.append(fk_desc)
            
            schema_desc = "\\n".join(description_parts)
            log_success("Schema description generated")
            
            return schema_desc
            
        except Exception as e:
            error_msg = f"Error describing schema: {str(e)}"
            log_error(error_msg)
            return error_msg

    def _validate_query(self, query: str) -> None:
        """Validate SQL query for safety."""
        query_lower = query.lower().strip()
        
        # Check for empty query
        if not query_lower:
            raise ValidationError("Query cannot be empty")
        
        # Warn about potentially dangerous operations
        dangerous_keywords = ["drop", "truncate", "delete from", "alter", "update", "insert", "create", "grant", "revoke"]
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                log_warning(f"Potentially dangerous query detected: contains '{keyword}'")

        # Enforce read-only mode unless explicitly allowed
        if not self.allow_write:
            allowed_starts = ("select", "with", "show", "describe", "explain")
            if not query_lower.startswith(allowed_starts):
                raise ValidationError("Write operations are disabled. Set SQL_ALLOW_WRITE=true to enable.")
        
        # Block certain operations in production
        blocked_keywords = ["drop database", "drop schema", "drop table"]
        for keyword in blocked_keywords:
            if keyword in query_lower:
                raise ValidationError(f"Query contains blocked operation: '{keyword}'")
        
        log_debug("Query validation passed")

    def format_results_for_agent(self, results: Dict[str, Any]) -> str:
        """Format query results for LLM consumption."""
        if not results["success"]:
            return f"Error executing query: {results.get('error', 'Unknown error')}"
        
        if not results["data"]:
            return f"Query executed successfully. {results['row_count']} rows affected."
        
        # Format as table
        lines = []
        lines.append(f"Query returned {results['row_count']} rows:\\n")
        
        # Add column headers
        columns = results["columns"]
        header = " | ".join(columns)
        separator = "-" * len(header)
        
        lines.append(header)
        lines.append(separator)
        
        # Add data rows (limit to prevent context overflow)
        max_display = min(10, len(results["data"]))
        for row in results["data"][:max_display]:
            row_str = " | ".join(str(row.get(col, "")) for col in columns)
            lines.append(row_str)
        
        if len(results["data"]) > max_display:
            lines.append(f"... and {len(results['data']) - max_display} more rows")
        
        return "\\n".join(lines)

    def get_sql_tool(self) -> "StructuredTool":
        """Get LangChain StructuredTool for SQL access."""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field

        class SQLQueryInput(BaseModel):
            query: str = Field(..., description="SQL query to execute")
            params: Optional[Dict[str, Any]] = Field(default=None, description="Optional query parameters")

        def _run_query(query: str, params: Optional[Dict[str, Any]] = None) -> str:
            results = self.execute_query(query, params=params)
            return self.format_results_for_agent(results)

        return StructuredTool.from_function(
            name="sql_query",
            description=(
                "Execute SQL queries against the application database. "
                "Use for admin-only data inspection and maintenance. "
                "Always prefer SELECT for read operations."
            ),
            func=_run_query,
            args_schema=SQLQueryInput,
        )

def ensure_db_schema() -> None:
    """Ensure core SQL tables exist (dev-friendly)."""
    try:
        engine = get_engine()
        inspector = inspect(engine)
        if not inspector.has_table("user"):
            log_info("Database tables missing. Initializing schema...")
            init_db()
            log_success("Database schema initialized")
    except Exception as e:
        log_warning(f"Database schema check failed: {e}")


# Factory function for creating SQL tool instances
def create_sql_tool(max_rows: int = 1000, timeout: int = 30) -> SQLTool:
    """Create a SQL tool instance."""
    log_info("Creating SQL tool for database information retrieval")
    return SQLTool(max_rows=max_rows, timeout=timeout)

sql_tool = SQLTool()