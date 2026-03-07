"""
Admin Service - System administration tasks
"""

from models.base import Base
from infrastructure.database.session import get_engine
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from utils.log import log_info, log_success, log_error
import models  # noqa: F401 - register models with Base


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
            if get_vector_db_tool().collection_exists():
                log_info(f"Deleting vector collection: {get_vector_db_tool().collection_name}")
                get_vector_db_tool().delete_collection()
            
            # Force full re-initialization (collection + vectorstore + services)
            log_info("Re-initializing vector database...")
            get_vector_db_tool().startup_check()
            log_success("Vector database reset successfully")

            return True

        except Exception as e:
            log_error(f"System reset failed: {e}")
            raise e
