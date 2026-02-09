"""SQL Schema Discovery and Caching Service.

This module provides intelligent schema discovery for LLM-based SQL generation,
implementing the DBCopilot approach:
- Tiered schema information (overview → detailed)
- Caching to avoid repeated introspection
- LLM-friendly schema descriptions
- Relationship mapping for JOIN guidance

Security:
- Read-only introspection (no data access)
- Configurable table filtering (exclude sensitive tables)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from infrastructure.dto.session import get_engine
from utils.log import log_debug, log_error, log_info, log_success, log_warning


# =============================================================================
# Configuration
# =============================================================================

# Tables to exclude from schema discovery (sensitive/internal)
DEFAULT_EXCLUDED_TABLES: Set[str] = {
    "alembic_version",
    "checkpoints",
    "checkpoint_writes", 
    "checkpoint_blobs",
}

# Schema cache TTL (in seconds)
SCHEMA_CACHE_TTL_SECONDS = int(os.getenv("SQL_SCHEMA_CACHE_TTL", "300"))


# =============================================================================
# Data Classes for Schema Information
# =============================================================================

@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_ref: Optional[str] = None  # "table.column" format
    default: Optional[str] = None
    description: Optional[str] = None

    def to_compact_str(self) -> str:
        """Return compact representation for LLM."""
        parts = [f"{self.name}: {self.data_type}"]
        if self.is_primary_key:
            parts.append("PK")
        if self.is_foreign_key and self.foreign_key_ref:
            parts.append(f"FK→{self.foreign_key_ref}")
        if not self.nullable:
            parts.append("NOT NULL")
        return " ".join(parts)


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    row_count_estimate: Optional[int] = None
    description: Optional[str] = None

    def to_compact_str(self, include_columns: bool = True) -> str:
        """Return compact representation for LLM."""
        parts = [f"**{self.name}**"]
        if self.row_count_estimate is not None:
            parts.append(f"(~{self.row_count_estimate} rows)")
        
        if include_columns and self.columns:
            col_strs = [c.to_compact_str() for c in self.columns]
            parts.append("\n  Columns: " + ", ".join(col_strs))
        
        if self.foreign_keys:
            fk_strs = []
            for fk in self.foreign_keys:
                local_cols = ", ".join(fk.get("constrained_columns", []))
                ref_table = fk.get("referred_table", "?")
                ref_cols = ", ".join(fk.get("referred_columns", []))
                fk_strs.append(f"{local_cols} → {ref_table}({ref_cols})")
            parts.append("\n  Relationships: " + "; ".join(fk_strs))
        
        return " ".join(parts)

    def get_column_names(self) -> List[str]:
        """Return list of column names."""
        return [c.name for c in self.columns]


@dataclass
class SchemaSnapshot:
    """Complete schema snapshot with metadata."""
    tables: Dict[str, TableInfo] = field(default_factory=dict)
    captured_at: datetime = field(default_factory=datetime.utcnow)
    database_name: Optional[str] = None
    database_version: Optional[str] = None

    def is_expired(self, ttl_seconds: int = SCHEMA_CACHE_TTL_SECONDS) -> bool:
        """Check if this snapshot has expired."""
        age = datetime.utcnow() - self.captured_at
        return age > timedelta(seconds=ttl_seconds)

    def get_table_names(self) -> List[str]:
        """Return sorted list of table names."""
        return sorted(self.tables.keys())

    def get_table(self, name: str) -> Optional[TableInfo]:
        """Get table info by name (case-insensitive)."""
        # Try exact match first
        if name in self.tables:
            return self.tables[name]
        # Try case-insensitive
        for tbl_name, tbl_info in self.tables.items():
            if tbl_name.lower() == name.lower():
                return tbl_info
        return None


# =============================================================================
# Schema Service
# =============================================================================

class SQLSchemaService:
    """Service for discovering and caching database schema information.
    
    Implements a tiered approach for LLM schema consumption:
    - Level 1: Table names only (minimal tokens)
    - Level 2: Tables with primary columns
    - Level 3: Full schema with relationships
    
    Usage:
        schema_service = SQLSchemaService()
        
        # For initial LLM context (minimal)
        overview = schema_service.get_schema_overview()
        
        # For specific table details
        table_info = schema_service.get_table_schema("user")
        
        # For SQL generation context
        context = schema_service.get_llm_context(["user", "thread"])
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        excluded_tables: Optional[Set[str]] = None,
        cache_ttl_seconds: int = SCHEMA_CACHE_TTL_SECONDS,
    ):
        """Initialize the schema service.
        
        Args:
            engine: SQLAlchemy engine (uses default if not provided)
            excluded_tables: Tables to exclude from discovery
            cache_ttl_seconds: How long to cache schema info
        """
        self._engine = engine
        self._excluded_tables = excluded_tables or DEFAULT_EXCLUDED_TABLES
        self._cache_ttl = cache_ttl_seconds
        self._cached_snapshot: Optional[SchemaSnapshot] = None
        log_debug("SQLSchemaService initialized")

    @property
    def engine(self) -> Engine:
        """Get the database engine (lazy initialization)."""
        if self._engine is None:
            self._engine = get_engine()
        return self._engine

    def _should_include_table(self, table_name: str) -> bool:
        """Check if a table should be included in schema discovery."""
        if table_name in self._excluded_tables:
            return False
        # Exclude tables starting with underscore (internal)
        if table_name.startswith("_"):
            return False
        return True

    def _get_row_count_estimate(self, table_name: str) -> Optional[int]:
        """Get estimated row count for a table (fast, may be approximate)."""
        try:
            with self.engine.connect() as conn:
                # Use PostgreSQL's statistics for fast estimate
                result = conn.execute(text(
                    "SELECT reltuples::bigint AS estimate "
                    "FROM pg_class WHERE relname = :table_name"
                ), {"table_name": table_name})
                row = result.fetchone()
                if row and row[0] >= 0:
                    return int(row[0])
        except Exception as e:
            log_debug(f"Could not get row count for {table_name}: {e}")
        return None

    def _discover_table(self, table_name: str, inspector) -> TableInfo:
        """Discover schema information for a single table."""
        columns: List[ColumnInfo] = []
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint.get("constrained_columns", []))
        
        # Get foreign keys for this table
        fk_info = inspector.get_foreign_keys(table_name)
        fk_map: Dict[str, str] = {}  # column -> "table.column"
        for fk in fk_info:
            for i, col in enumerate(fk.get("constrained_columns", [])):
                ref_table = fk.get("referred_table", "")
                ref_cols = fk.get("referred_columns", [])
                if ref_cols and len(ref_cols) > i:
                    fk_map[col] = f"{ref_table}.{ref_cols[i]}"
        
        # Get columns
        for col in inspector.get_columns(table_name):
            col_name = col["name"]
            col_type = str(col.get("type", "UNKNOWN"))
            # Simplify type names for LLM
            col_type = col_type.split("(")[0]  # Remove precision
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=col_type,
                nullable=col.get("nullable", True),
                is_primary_key=col_name in pk_columns,
                is_foreign_key=col_name in fk_map,
                foreign_key_ref=fk_map.get(col_name),
                default=str(col.get("default", "")) if col.get("default") else None,
            ))
        
        # Get indexes
        indexes = []
        for idx in inspector.get_indexes(table_name):
            idx_cols = ", ".join(idx.get("column_names", []))
            indexes.append(f"{idx['name']}({idx_cols})")
        
        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=list(pk_columns),
            foreign_keys=fk_info,
            indexes=indexes,
            row_count_estimate=self._get_row_count_estimate(table_name),
        )

    def discover_schema(self, force_refresh: bool = False) -> SchemaSnapshot:
        """Discover complete database schema.
        
        Args:
            force_refresh: If True, bypass cache and rediscover
            
        Returns:
            SchemaSnapshot with all discovered tables
        """
        # Check cache
        if not force_refresh and self._cached_snapshot:
            if not self._cached_snapshot.is_expired(self._cache_ttl):
                log_debug("Returning cached schema snapshot")
                return self._cached_snapshot
        
        log_info("Discovering database schema...")
        inspector = inspect(self.engine)
        
        # Get database info
        db_name = None
        db_version = None
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT current_database(), version()"))
                row = result.fetchone()
                if row:
                    db_name = row[0]
                    db_version = row[1].split(",")[0] if row[1] else None
        except Exception as e:
            log_debug(f"Could not get database info: {e}")
        
        # Discover all tables
        tables: Dict[str, TableInfo] = {}
        for table_name in inspector.get_table_names():
            if not self._should_include_table(table_name):
                continue
            try:
                tables[table_name] = self._discover_table(table_name, inspector)
            except Exception as e:
                log_warning(f"Failed to discover table {table_name}: {e}")
        
        snapshot = SchemaSnapshot(
            tables=tables,
            captured_at=datetime.utcnow(),
            database_name=db_name,
            database_version=db_version,
        )
        
        # Update cache
        self._cached_snapshot = snapshot
        log_success(f"Schema discovery complete: {len(tables)} tables found")
        
        return snapshot

    def get_schema_overview(self) -> str:
        """Get minimal schema overview (table names only).
        
        Ideal for initial LLM context to minimize tokens.
        
        Returns:
            Formatted string with table names
        """
        snapshot = self.discover_schema()
        
        lines = [
            f"Database: {snapshot.database_name or 'Unknown'}",
            f"Tables ({len(snapshot.tables)}):",
        ]
        
        for name in snapshot.get_table_names():
            table = snapshot.tables[name]
            row_info = f" (~{table.row_count_estimate} rows)" if table.row_count_estimate else ""
            lines.append(f"  - {name}{row_info}")
        
        return "\n".join(lines)

    def get_table_schema(self, table_name: str) -> Optional[str]:
        """Get detailed schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Formatted schema string, or None if table not found
        """
        snapshot = self.discover_schema()
        table = snapshot.get_table(table_name)
        
        if not table:
            return None
        
        return table.to_compact_str(include_columns=True)

    def get_llm_context(
        self,
        relevant_tables: Optional[List[str]] = None,
        include_relationships: bool = True,
        max_tables: int = 10,
    ) -> str:
        """Get LLM-optimized schema context.
        
        This generates a context string optimized for SQL generation:
        - Detailed info for relevant tables
        - Relationship hints for JOINs
        - Sample column types for proper value formatting
        
        Args:
            relevant_tables: Tables to include in detail (if None, includes all)
            include_relationships: Whether to include FK relationships
            max_tables: Maximum tables to include in detail
            
        Returns:
            Formatted context string for LLM
        """
        snapshot = self.discover_schema()
        
        # Determine which tables to include in detail
        if relevant_tables:
            detail_tables = [t for t in relevant_tables if snapshot.get_table(t)]
        else:
            detail_tables = snapshot.get_table_names()[:max_tables]
        
        lines = [
            "## Database Schema",
            "",
            f"Database: {snapshot.database_name or 'PostgreSQL'}",
            "",
        ]
        
        # Add detailed table info
        for table_name in detail_tables:
            table = snapshot.get_table(table_name)
            if not table:
                continue
            
            lines.append(f"### Table: {table.name}")
            
            # Columns
            lines.append("**Columns:**")
            for col in table.columns:
                markers = []
                if col.is_primary_key:
                    markers.append("PK")
                if col.is_foreign_key:
                    markers.append(f"FK→{col.foreign_key_ref}")
                if not col.nullable:
                    markers.append("NOT NULL")
                
                marker_str = f" [{', '.join(markers)}]" if markers else ""
                lines.append(f"- `{col.name}`: {col.data_type}{marker_str}")
            
            # Relationships
            if include_relationships and table.foreign_keys:
                lines.append("")
                lines.append("**Relationships:**")
                for fk in table.foreign_keys:
                    local_cols = ", ".join(fk.get("constrained_columns", []))
                    ref_table = fk.get("referred_table", "?")
                    ref_cols = ", ".join(fk.get("referred_columns", []))
                    lines.append(f"- {local_cols} → {ref_table}({ref_cols})")
            
            lines.append("")
        
        # Add overview of other tables
        other_tables = [t for t in snapshot.get_table_names() if t not in detail_tables]
        if other_tables:
            lines.append("### Other Available Tables")
            lines.append(", ".join(other_tables))
            lines.append("")
        
        return "\n".join(lines)

    def infer_relevant_tables(self, query: str) -> List[str]:
        """Infer which tables might be relevant for a natural language query.
        
        Uses keyword matching to suggest tables. This is a heuristic
        that can be enhanced with embeddings or LLM assistance.
        
        Args:
            query: Natural language query
            
        Returns:
            List of potentially relevant table names
        """
        snapshot = self.discover_schema()
        query_lower = query.lower()
        
        # Simple keyword matching
        keyword_map = {
            "user": ["user", "user_profile"],
            "account": ["user", "user_profile"],
            "message": ["message", "thread"],
            "chat": ["message", "thread"],
            "conversation": ["thread", "message"],
            "thread": ["thread"],
            "run": ["run"],
            "execution": ["run"],
            "tool": ["tool_usage"],
            "audit": ["audit_log"],
            "log": ["audit_log", "tool_usage"],
            "memory": ["thread_summaries"],
            "summary": ["thread_summaries"],
        }
        
        relevant = set()
        for keyword, tables in keyword_map.items():
            if keyword in query_lower:
                for t in tables:
                    if snapshot.get_table(t):
                        relevant.add(t)
        
        # If no matches, include common tables
        if not relevant:
            for default_table in ["user", "thread", "message"]:
                if snapshot.get_table(default_table):
                    relevant.add(default_table)
        
        return list(relevant)

    def validate_table_references(self, sql: str) -> Tuple[bool, List[str]]:
        """Validate that all table references in SQL exist.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, list of invalid table names)
        """
        snapshot = self.discover_schema()
        valid_tables = set(snapshot.get_table_names())
        
        # Match FROM and JOIN clauses
        patterns = [
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        referenced_tables = set()
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            referenced_tables.update(t.lower() for t in matches)
        
        # Check which are invalid
        invalid = []
        for table in referenced_tables:
            # Case-insensitive check
            found = any(t.lower() == table for t in valid_tables)
            if not found:
                invalid.append(table)
        
        return len(invalid) == 0, invalid

    def clear_cache(self) -> None:
        """Clear the cached schema snapshot."""
        self._cached_snapshot = None
        log_debug("Schema cache cleared")


# =============================================================================
# Singleton Instance
# =============================================================================

sql_schema_service = SQLSchemaService()
