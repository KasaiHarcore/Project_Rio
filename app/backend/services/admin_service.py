"""
Admin Service - System administration tasks
"""

from backend.db.base import Base
from backend.db.session import get_engine
from backend.services.tools.qdrant_tool import vector_db_tool
from backend.utils.log import log_info, log_success, log_error
import backend.db.models


class AdminService:
    @staticmethod
    def reset_database() -> bool:
        """
        Completely reset the system:
        1. Drop all SQL tables
        2. Recreate all SQL tables
        3. Delete and recreate Qdrant vector collection
        """
        try:
            engine = get_engine()
            log_info("Starting full system reset...")

            # 1. Reset SQL Database
            log_info("Dropping all database tables...")
            Base.metadata.drop_all(engine)
            log_info("Recreating all database tables...")
            Base.metadata.create_all(engine)
            log_success("SQL database reset successfully")

            # 2. Reset Vector Database
            if vector_db_tool.collection_exists():
                log_info(f"Deleting vector collection: {vector_db_tool.collection_name}")
                vector_db_tool.delete_collection()
            
            log_info("Re-initializing vector collection...")
            vector_db_tool._ensure_collection()
            log_success("Vector database reset successfully")

            return True

        except Exception as e:
            log_error(f"System reset failed: {e}")
            raise e
