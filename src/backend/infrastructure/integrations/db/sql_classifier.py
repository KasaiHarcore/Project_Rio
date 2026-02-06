"""SQL Operation Classification and Safety.

This module provides SQL operation classification to distinguish
between READ (safe) and WRITE (dangerous) operations, enabling
appropriate HITL approval workflows.

Key Features:
- Accurate SQL operation type detection
- Danger level assessment
- Affected table extraction
- Safety policy enforcement
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Tuple

from backend.utils.log import log_debug, log_warning


# =============================================================================
# Enums and Constants
# =============================================================================

class SQLOperationType(Enum):
    """Type of SQL operation."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    ALTER = "ALTER"
    DROP = "DROP"
    TRUNCATE = "TRUNCATE"
    GRANT = "GRANT"
    REVOKE = "REVOKE"
    EXECUTE = "EXECUTE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_read_only(self) -> bool:
        """Check if this operation type is read-only."""
        return self == SQLOperationType.SELECT

    @property
    def is_destructive(self) -> bool:
        """Check if this operation can destroy data."""
        return self in {
            SQLOperationType.DELETE,
            SQLOperationType.DROP,
            SQLOperationType.TRUNCATE,
        }

    @property
    def is_schema_change(self) -> bool:
        """Check if this operation modifies schema."""
        return self in {
            SQLOperationType.CREATE,
            SQLOperationType.ALTER,
            SQLOperationType.DROP,
        }


class DangerLevel(Enum):
    """Danger level of an SQL operation."""
    SAFE = "safe"           # Read-only, no approval needed
    LOW = "low"             # Single-row insert/update
    MEDIUM = "medium"       # Multi-row modifications
    HIGH = "high"           # Delete, bulk update
    CRITICAL = "critical"   # DDL, drop, truncate

    @property
    def requires_approval(self) -> bool:
        """Check if this danger level requires user approval."""
        return self in {DangerLevel.MEDIUM, DangerLevel.HIGH, DangerLevel.CRITICAL}

    @property
    def allows_auto_execute(self) -> bool:
        """Check if this danger level allows auto-execution."""
        return self in {DangerLevel.SAFE, DangerLevel.LOW}


class ApprovalPolicy(Enum):
    """Approval policy for SQL operations."""
    AUTO = "auto"           # No approval needed
    NOTIFY = "notify"       # Notify user, but execute
    CONFIRM = "confirm"     # Require explicit approval
    ADMIN_ONLY = "admin_only"  # Only admins can approve

    @property
    def requires_approval(self) -> bool:
        """Check if this policy requires explicit user approval."""
        return self in {ApprovalPolicy.CONFIRM, ApprovalPolicy.ADMIN_ONLY}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SQLClassification:
    """Classification result for an SQL query."""
    sql: str
    operation_type: SQLOperationType
    danger_level: DangerLevel
    affected_tables: List[str]
    is_multi_statement: bool
    has_where_clause: bool
    has_limit: bool
    estimated_rows_affected: Optional[str] = None  # "single", "multiple", "all", "unknown"
    warnings: List[str] = None
    approval_policy: ApprovalPolicy = ApprovalPolicy.AUTO

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        # Auto-determine approval policy
        self.approval_policy = self._determine_policy()

    def _determine_policy(self) -> ApprovalPolicy:
        """Determine the approval policy based on classification."""
        if self.operation_type.is_read_only:
            return ApprovalPolicy.AUTO
        
        if self.danger_level == DangerLevel.CRITICAL:
            return ApprovalPolicy.ADMIN_ONLY
        
        if self.danger_level == DangerLevel.HIGH:
            return ApprovalPolicy.CONFIRM
        
        if self.danger_level == DangerLevel.MEDIUM:
            return ApprovalPolicy.CONFIRM
        
        if self.danger_level == DangerLevel.LOW:
            return ApprovalPolicy.NOTIFY
        
        return ApprovalPolicy.AUTO

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        parts = [
            f"Operation: {self.operation_type.value}",
            f"Danger Level: {self.danger_level.value.upper()}",
            f"Affected Tables: {', '.join(self.affected_tables) or 'None detected'}",
        ]
        
        if self.estimated_rows_affected:
            parts.append(f"Rows Affected: {self.estimated_rows_affected}")
        
        if self.warnings:
            parts.append(f"Warnings: {'; '.join(self.warnings)}")
        
        parts.append(f"Approval: {self.approval_policy.value}")
        
        return "\n".join(parts)


# =============================================================================
# SQL Classifier
# =============================================================================

class SQLClassifier:
    """Classifier for SQL operations.
    
    Analyzes SQL queries to determine their operation type, danger level,
    and appropriate approval policy.
    
    Usage:
        classifier = SQLClassifier()
        result = classifier.classify("SELECT * FROM user WHERE id = 1")
        
        if result.danger_level.requires_approval:
            # Trigger HITL approval flow
            ...
    """

    # Patterns for operation detection (order matters - first match wins)
    OPERATION_PATTERNS = [
        (r'^\s*SELECT\b', SQLOperationType.SELECT),
        (r'^\s*INSERT\b', SQLOperationType.INSERT),
        (r'^\s*UPDATE\b', SQLOperationType.UPDATE),
        (r'^\s*DELETE\b', SQLOperationType.DELETE),
        (r'^\s*CREATE\b', SQLOperationType.CREATE),
        (r'^\s*ALTER\b', SQLOperationType.ALTER),
        (r'^\s*DROP\b', SQLOperationType.DROP),
        (r'^\s*TRUNCATE\b', SQLOperationType.TRUNCATE),
        (r'^\s*GRANT\b', SQLOperationType.GRANT),
        (r'^\s*REVOKE\b', SQLOperationType.REVOKE),
        (r'^\s*EXEC(?:UTE)?\b', SQLOperationType.EXECUTE),
    ]

    # Patterns for table extraction
    TABLE_PATTERNS = [
        r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bTABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\bTRUNCATE\s+(?:TABLE\s+)?([a-zA-Z_][a-zA-Z0-9_]*)',
    ]

    # Sensitive tables that elevate danger level
    SENSITIVE_TABLES: Set[str] = {
        "user", "users", "admin", "admins",
        "auth", "authentication",
        "password", "passwords",
        "credential", "credentials",
        "secret", "secrets",
        "token", "tokens",
        "session", "sessions",
        "permission", "permissions",
        "role", "roles",
    }

    def __init__(self, sensitive_tables: Optional[Set[str]] = None):
        """Initialize classifier.
        
        Args:
            sensitive_tables: Additional sensitive table names
        """
        self._sensitive_tables = self.SENSITIVE_TABLES.copy()
        if sensitive_tables:
            self._sensitive_tables.update(sensitive_tables)

    def _detect_operation_type(self, sql: str) -> SQLOperationType:
        """Detect the primary operation type of the SQL."""
        sql_upper = sql.upper()
        
        for pattern, op_type in self.OPERATION_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return op_type
        
        return SQLOperationType.UNKNOWN

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names referenced in the SQL."""
        tables = set()
        
        for pattern in self.TABLE_PATTERNS:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.update(t.lower() for t in matches)
        
        # Remove common SQL keywords that might be false positives
        keywords = {"select", "from", "where", "and", "or", "not", "null", "true", "false"}
        tables -= keywords
        
        return sorted(tables)

    def _has_where_clause(self, sql: str) -> bool:
        """Check if SQL has a WHERE clause."""
        return bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))

    def _has_limit_clause(self, sql: str) -> bool:
        """Check if SQL has a LIMIT clause."""
        return bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE))

    def _is_multi_statement(self, sql: str) -> bool:
        """Check if SQL contains multiple statements."""
        # Remove string literals to avoid false positives
        clean_sql = re.sub(r"'[^']*'", "", sql)
        clean_sql = re.sub(r'"[^"]*"', "", clean_sql)
        return clean_sql.count(";") > 1

    def _estimate_rows_affected(
        self,
        sql: str,
        op_type: SQLOperationType,
        has_where: bool,
        has_limit: bool,
    ) -> Optional[str]:
        """Estimate how many rows will be affected."""
        if op_type == SQLOperationType.SELECT:
            if has_limit:
                return "limited"
            return "unknown"
        
        if op_type in {SQLOperationType.INSERT}:
            # Check for VALUES clauses
            values_count = sql.upper().count("VALUES")
            if values_count == 1:
                return "single"
            elif values_count > 1:
                return "multiple"
            # INSERT ... SELECT
            if re.search(r'\bSELECT\b', sql, re.IGNORECASE):
                return "multiple"
            return "single"
        
        if op_type in {SQLOperationType.UPDATE, SQLOperationType.DELETE}:
            if not has_where:
                return "all"
            # Check for specific ID conditions
            if re.search(r'\b(id|pk)\s*=\s*\d+', sql, re.IGNORECASE):
                return "single"
            return "multiple"
        
        if op_type == SQLOperationType.TRUNCATE:
            return "all"
        
        return "unknown"

    def _assess_danger_level(
        self,
        op_type: SQLOperationType,
        affected_tables: List[str],
        has_where: bool,
        has_limit: bool,
        is_multi_statement: bool,
        rows_affected: Optional[str],
    ) -> Tuple[DangerLevel, List[str]]:
        """Assess the danger level of the operation."""
        warnings = []
        
        # Start with base level by operation type
        if op_type == SQLOperationType.SELECT:
            return DangerLevel.SAFE, warnings
        
        # Critical operations
        if op_type in {SQLOperationType.DROP, SQLOperationType.TRUNCATE}:
            warnings.append(f"{op_type.value} is a destructive operation")
            return DangerLevel.CRITICAL, warnings
        
        if op_type in {SQLOperationType.CREATE, SQLOperationType.ALTER}:
            warnings.append(f"{op_type.value} modifies database schema")
            return DangerLevel.CRITICAL, warnings
        
        if op_type in {SQLOperationType.GRANT, SQLOperationType.REVOKE}:
            warnings.append(f"{op_type.value} modifies permissions")
            return DangerLevel.CRITICAL, warnings
        
        # Multi-statement is always higher risk
        if is_multi_statement:
            warnings.append("Multiple statements detected")
            return DangerLevel.HIGH, warnings
        
        # Check for sensitive tables
        sensitive_affected = [t for t in affected_tables if t in self._sensitive_tables]
        if sensitive_affected:
            warnings.append(f"Affects sensitive table(s): {', '.join(sensitive_affected)}")
            # Elevate danger level
            if op_type == SQLOperationType.DELETE:
                return DangerLevel.CRITICAL, warnings
            return DangerLevel.HIGH, warnings
        
        # DELETE operations
        if op_type == SQLOperationType.DELETE:
            if not has_where:
                warnings.append("DELETE without WHERE clause affects all rows")
                return DangerLevel.CRITICAL, warnings
            if rows_affected == "all":
                return DangerLevel.HIGH, warnings
            if rows_affected == "single":
                return DangerLevel.MEDIUM, warnings
            return DangerLevel.HIGH, warnings
        
        # UPDATE operations
        if op_type == SQLOperationType.UPDATE:
            if not has_where:
                warnings.append("UPDATE without WHERE clause affects all rows")
                return DangerLevel.HIGH, warnings
            if rows_affected == "single":
                return DangerLevel.LOW, warnings
            return DangerLevel.MEDIUM, warnings
        
        # INSERT operations
        if op_type == SQLOperationType.INSERT:
            if rows_affected == "single":
                return DangerLevel.LOW, warnings
            return DangerLevel.MEDIUM, warnings
        
        # Default for unknown operations
        warnings.append(f"Unknown operation type: {op_type.value}")
        return DangerLevel.HIGH, warnings

    def classify(self, sql: str) -> SQLClassification:
        """Classify an SQL query.
        
        Args:
            sql: SQL query to classify
            
        Returns:
            SQLClassification with operation details
        """
        sql = sql.strip()
        
        # Basic analysis
        op_type = self._detect_operation_type(sql)
        affected_tables = self._extract_tables(sql)
        has_where = self._has_where_clause(sql)
        has_limit = self._has_limit_clause(sql)
        is_multi = self._is_multi_statement(sql)
        rows_affected = self._estimate_rows_affected(sql, op_type, has_where, has_limit)
        
        # Assess danger
        danger_level, warnings = self._assess_danger_level(
            op_type, affected_tables, has_where, has_limit, is_multi, rows_affected
        )
        
        classification = SQLClassification(
            sql=sql,
            operation_type=op_type,
            danger_level=danger_level,
            affected_tables=affected_tables,
            is_multi_statement=is_multi,
            has_where_clause=has_where,
            has_limit=has_limit,
            estimated_rows_affected=rows_affected,
            warnings=warnings,
        )
        
        log_debug(
            f"SQL classified: {op_type.value}, "
            f"danger={danger_level.value}, "
            f"tables={affected_tables}"
        )
        
        return classification


# =============================================================================
# Singleton Instance
# =============================================================================

sql_classifier = SQLClassifier()
