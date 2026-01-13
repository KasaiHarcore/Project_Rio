from typing import Any, Tuple, List, Dict, Optional
import traceback
import json

from sqlalchemy import create_engine, inspect, MetaData, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.tools import tool

from app.backend.utils.log import log_info, log_error, log_success
from typing import Any, List, Dict, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
class QueryInput(BaseModel):
    spec: dict = Field(description="JSON specification for the SQL query action")

class TableSchemaInput(BaseModel):
    table_name: Optional[str] = Field(default=None, description="Specific table name to inspect")

class PostgresDatabaseManager:
    def __init__(self):
        self.engine = None
        self.allowed_ops = {"=", "!=", "<", ">", "<=", ">=", "IN", "LIKE"}
        self.is_expression_allowed = {}
        self._metadata = None

    def connect(
        self,
        host: str,
        port: str,
        database: str,
        user: str,
        password: str
    ) -> bool:
        """
        Establish connection to PostgreSQL database.
        """
        try:
            # Close existing connection if any
            if self.engine:
                self.engine.dispose()

            # Build connection string
            connection_string = (
                f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
            )

            # Create engine
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,
                max_overflow=10,
                echo=False  # Set to True for SQL query logging
            )

            # Initialize metadata
            self._metadata = MetaData()

            return True

        except SQLAlchemyError as e:
            log_error(f"Database connection error: {str(e)}")
            self.engine = None
            return False

        except Exception as e:
            log_error(f"Unexpected error during connection: {str(e)}")
            self.engine = None
            return False

    def get_table_schema(self, table_name: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Get database schema information for all tables or a specific table.
        """
        if not self.engine:
            return "", "Not connected to database"

        try:
            inspector = inspect(self.engine)

            # Get all table names
            all_tables = inspector.get_table_names()

            if not all_tables:
                return "No tables found in database", None

            # Filter to specific table if requested
            if table_name:
                if table_name not in all_tables:
                    return "", f"Table '{table_name}' not found in database"
                tables_to_process = [table_name]
            else:
                tables_to_process = all_tables

            # Build schema text
            schema_parts = []
            schema_parts.append("DATABASE SCHEMA")
            schema_parts.append("=" * 80)
            schema_parts.append("")

            for tbl in tables_to_process:
                schema_parts.append(f"Table: {tbl}")
                schema_parts.append("-" * 80)

                # Get columns
                columns = inspector.get_columns(tbl)
                schema_parts.append("Columns:")
                for col in columns:
                    col_type = str(col['type'])
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    default = f", DEFAULT: {col['default']}" if col.get('default') else ""
                    schema_parts.append(f"  - {col['name']}: {col_type} {nullable}{default}")

                # Get primary keys
                pk = inspector.get_pk_constraint(tbl)
                if pk and pk.get('constrained_columns'):
                    schema_parts.append(f"\nPrimary Key: {', '.join(pk['constrained_columns'])}")

                # Get foreign keys
                fks = inspector.get_foreign_keys(tbl)
                if fks:
                    schema_parts.append("\nForeign Keys:")
                    for fk in fks:
                        fk_cols = ', '.join(fk['constrained_columns'])
                        ref_table = fk['referred_table']
                        ref_cols = ', '.join(fk['referred_columns'])
                        schema_parts.append(f"  - {fk_cols} -> {ref_table}({ref_cols})")

                # Get indexes
                indexes = inspector.get_indexes(tbl)
                if indexes:
                    schema_parts.append("\nIndexes:")
                    for idx in indexes:
                        idx_cols = ', '.join(idx['column_names'])
                        unique = "UNIQUE" if idx.get('unique') else ""
                        schema_parts.append(f"  - {idx['name']}: {idx_cols} {unique}")

                schema_parts.append("")
                schema_parts.append("")

            return "\n".join(schema_parts), None

        except SQLAlchemyError as e:
            error_msg = f"SQLAlchemy error: {str(e)}"
            return "", error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return "", error_msg

    def select_rows(self, spec: json):
        """
        SQL Select operation based on json provided format
        """
        if spec.get("action") != "select":
            return [], "Invalid action"

        target = spec["target"]
        query = spec["query"]

        base_table = target["table"]
        base_alias = target.get("alias", base_table)

        params = {}
        param_counter = 0

        # ---------- SELECT ----------
        select_parts = []
        for col in query["columns"]:
            expr = col["expr"]
            alias = col.get("as")
            select_parts.append(f"{expr} AS {alias}" if alias else expr)

        distinct_sql = "DISTINCT " if query.get("distinct") else ""
        select_sql = f"SELECT {distinct_sql}{', '.join(select_parts)}"

        # ---------- FROM ----------
        from_sql = f"FROM {base_table} {base_alias}"

        # ---------- JOIN ----------
        join_sql = ""
        for j in query.get("joins", []):
            jtype = j.get("type", "inner").upper()
            table = j["table"]
            alias = j.get("alias", table)

            on_parts = []
            for cond in j["on"]:
                on_parts.append(f"{cond['left']} {cond['op']} {cond['right']}")

            join_sql += f" {jtype} JOIN {table} {alias} ON {' AND '.join(on_parts)}"

        # ---------- WHERE ----------
        where_parts = []
        for cond in query.get("where", []):
            if cond["op"].upper() not in self.allowed_ops:
                return [], f"Operator not allowed: {cond['op']}"

            key = f"p{param_counter}"
            param_counter += 1

            where_parts.append(f"{cond['left']} {cond['op']} :{key}")
            params[key] = cond["value"]

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # ---------- GROUP BY ----------
        group_sql = ""
        if "group_by" in query:
            group_sql = "GROUP BY " + ", ".join(query["group_by"])

        # ---------- HAVING ----------
        having_parts = []
        for cond in query.get("having", []):
            key = f"p{param_counter}"
            param_counter += 1
            having_parts.append(f"{cond['expr']} {cond['op']} :{key}")
            params[key] = cond["value"]

        having_sql = f"HAVING {' AND '.join(having_parts)}" if having_parts else ""

        # ---------- ORDER BY ----------
        order_sql = ""
        if "order_by" in query:
            order_sql = "ORDER BY " + ", ".join(
                f"{o['expr']} {o.get('direction', 'ASC').upper()}"
                for o in query["order_by"]
            )

        # ---------- LIMIT / OFFSET ----------
        limit_sql = ""
        if "limit" in query:
            limit_sql += f" LIMIT {int(query['limit'])}"
        if "offset" in query:
            limit_sql += f" OFFSET {int(query['offset'])}"

        # ---------- FINAL SQL ----------
        sql = f"""
        {select_sql}
        {from_sql}
        {join_sql}
        {where_sql}
        {group_sql}
        {having_sql}
        {order_sql}
        {limit_sql}
        """

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                return [dict(row) for row in result.mappings()], None

        except SQLAlchemyError as e:
            return [], str(e)
      

    def update_rows(self, spec: json):
        """
        SQL update operation based on json provided format
        """
        if spec.get("action") != "update":
            return [], "Invalid action"

        target = spec["target"]
        query = spec["query"]

        table = target["table"]
        alias = target.get("alias", table)

        params = {}
        param_counter = 0

        # ---------- UPDATE ---------
        update_sql = f"UPDATE {table} {alias}"

        # ---------- SET ----------
        set_parts = []

        # SET value (bind param)
        for col, val in query.get("set", {}).items():
            key = f"p{param_counter}"
            param_counter += 1
            set_parts.append(f"{col} = :{key}")
            params[key] = val

        # SET expression (raw SQL but whitelisted)
        for col, expr in query.get("set_expr", {}).items():
            if not self.is_expr_allowed(col, expr):
                return [], f"Expression not allowed: {col} = {expr}"
            set_parts.append(f"{col} = {expr}")

        if not set_parts:
            return [], "Nothing to update"

        set_sql = "SET " + ", ".join(set_parts)

        # ---------- FROM ----------
        from_parts = []
        where_parts = []

        for frm in query.get("from", []):
            tbl = frm["table"]
            als = frm.get("alias", tbl)
            from_parts.append(f"{tbl} {als}")

            for cond in frm.get("on", []):
                where_parts.append(
                    f"{cond['left']} {cond['op']} {cond['right']}"
                )

        from_sql = f"FROM {', '.join(from_parts)}" if from_parts else ""

        # ---------- WHERE ----------
        for cond in query.get("where", []):
            if cond["op"].upper() not in self.allowed_ops:
                return [], f"Operator not allowed: {cond['op']}"

            key = f"p{param_counter}"
            param_counter += 1
            where_parts.append(f"{cond['left']} {cond['op']} :{key}")
            params[key] = cond["value"]

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # ---------- RETURNING ----------
        returning_sql = ""
        if "returning" in query:
            returning_sql = "RETURNING " + ", ".join(query["returning"])

        # ---------- FINAL SQL ----------
        sql = f"""
        {update_sql}
        {set_sql}
        {from_sql}
        {where_sql}
        {returning_sql}
        """

        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql), params)
                return [dict(row) for row in result.mappings()], None

        except SQLAlchemyError as e:
            return [], str(e)
    

    def delete_rows(self, spec: json):
        """
        SQL delete operation based on json provided format
        """
        if spec.get("action") != "delete":
            return [], "Invalid action"

        target = spec["target"]
        query = spec["query"]

        params = {}
        param_counter = 0

        table = target["table"]
        alias = target["alias"]

        # ---------- DELETE ----------
        delete_sql = f"DELETE FROM {table} {alias}"

        # ---------- USING ----------
        using_tables = []
        join_conditions = []

        for j in query.get("using", []):
            using_tables.append(f"{j['table']} {j['alias']}")
            for cond in j.get("on", []):
                join_conditions.append(
                    f"{cond['left']} {cond['op']} {cond['right']}"
                )

        using_sql = ""
        if using_tables:
            using_sql = "USING " + ", ".join(using_tables)

        # ---------- WHERE ----------
        where_parts = []

        where_parts.extend(join_conditions)

        for k in query.get("where", []):
            if k["op"].upper() not in self.allowed_ops:
                return [], f"Operator not allowed: {k['op']}"

            key = f"p{param_counter}"
            param_counter += 1

            where_parts.append(f"{k['left']} {k['op']} :{key}")
            params[key] = k["value"]

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        # ---------- ORDER BY ----------
        order_sql = ""
        if "order_by" in query:
            order_sql = "ORDER BY " + ", ".join(
                f"{o['expr']} {o.get('direction', 'ASC').upper()}"
                for o in query["order_by"]
            )

        # ---------- RETURNING ----------
        returning_sql = ""
        if "returning" in query:
            returning_sql = "RETURNING " + ", ".join(query["returning"])

        # ---------- FINAL SQL ----------
        sql = f"""
        {delete_sql}
        {using_sql}
        {where_sql}
        {order_sql}
        {returning_sql}
        """

        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql), params)
                return [dict(row) for row in result.mappings()], None

        except SQLAlchemyError as e:
            return [], str(e)

    def insert_rows(self, spec: json):
        """
        SQL insert operation based on json provided format
        """
        if spec.get("action") != "insert":
            return [], "Invalid action"

        target = spec["target"]
        data = spec["data"]
        options = spec.get("options", {})
        returning = spec.get("returning")

        table = target["table"]

        # ---------- VALIDATE DATA ----------
        rows = data.get("rows", [])
        if len(rows) != 1:
            return [], "Insert expects exactly one batch object in rows"

        batch = rows[0]

        # validate vector lengths
        lengths = {len(v) for v in batch.values()}
        if len(lengths) != 1:
            return [], "All column arrays must have the same length"

        row_count = lengths.pop()
        if row_count == 0:
            return [], "No rows to insert"

        columns = list(batch.keys())

        # ---------- BUILD INSERT ----------
        insert_sql = f"INSERT INTO {table} ({', '.join(columns)})"

        values_sql = []
        params = {}

        for row_idx in range(row_count):
            placeholders = []

            for col in columns:
                val = batch[col][row_idx]

                # SQL expression
                if isinstance(val, dict) and "expr" in val:
                    placeholders.append(val["expr"])
                else:
                    key = f"{col}_{row_idx}"
                    placeholders.append(f":{key}")
                    params[key] = val

            values_sql.append("(" + ", ".join(placeholders) + ")")

        values_sql = "VALUES " + ", ".join(values_sql)

        # ---------- ON CONFLICT ----------
        conflict_sql = ""
        on_conflict = options.get("on_conflict")
        if on_conflict:
            cols = ", ".join(on_conflict["columns"])
            action = on_conflict["action"]

            if action == "nothing":
                conflict_sql = f"ON CONFLICT ({cols}) DO NOTHING"

            elif action == "update":
                sets = []
                for col, val in on_conflict.get("set", {}).items():
                    if isinstance(val, dict) and "excluded" in val:
                        sets.append(f"{col} = EXCLUDED.{val['excluded']}")
                    elif isinstance(val, dict) and "expr" in val:
                        sets.append(f"{col} = {val['expr']}")
                    else:
                        key = f"conf_{col}"
                        sets.append(f"{col} = :{key}")
                        params[key] = val

                conflict_sql = (
                    f"ON CONFLICT ({cols}) DO UPDATE SET "
                    + ", ".join(sets)
                )
            else:
                return [], f"Invalid on_conflict action: {action}"

        # ---------- RETURNING ----------
        returning_sql = ""
        if returning:
            returning_sql = "RETURNING " + ", ".join(returning)

        # ---------- FINAL SQL ----------
        sql = f"""
        {insert_sql}
        {values_sql}
        {conflict_sql}
        {returning_sql}
        """

        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql), params)
                return [dict(r) for r in result.mappings()], None

        except SQLAlchemyError as e:
            return [], str(e)

    def close(self):
        """
        Close database connection and dispose of engine.
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self._metadata = None

def get_postgres_tools() -> List[StructuredTool]:
    """
    Initialize Postgres Toolkit
    """
    db_manager = PostgresDatabaseManager()

    tools = [
        StructuredTool.from_function(
            func=db_manager.connect,
            name="connect_db",
            description="Connect to Postgres DB"
        ),
        StructuredTool.from_function(
            func=db_manager.get_table_schema,
            name="get_schema",
            description="Get schema info of tables.",
            args_schema=TableSchemaInput
        ),
        StructuredTool.from_function(
            func=db_manager.select_rows,
            name="select_rows",
            description="Execute SQL SELECT based on a JSON specification.",
            args_schema=QueryInput
        ),
        StructuredTool.from_function(
            func=db_manager.insert_rows,
            name="insert_rows",
            description="Execute SQL INSERT based on a JSON specification.",
            args_schema=QueryInput
        ),
        StructuredTool.from_function(
            func=db_manager.delete_rows,
            name="delete_rows",
            description="Execute SQL DELETE based on a JSON specification.",
            args_schema=QueryInput
        ),
        StructuredTool.from_function(
            func=db_manager.update_rows,
            name="update_rows",
            description="Execute SQL UPDATE based on a JSON specification.",
            args_schema=QueryInput
        ),
        StructuredTool.from_function(
            func=db_manager.close,
            name="close_db",
            description="Close the database connection."
        )
    ]
    return tools