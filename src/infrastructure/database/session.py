"""Database Session Creation and Lifecycle Management.

This module provides:
- Engine creation with connection pooling
- Session factory for database connections
- Context managers for session lifecycle
- Development helpers (init_db, drop_db)

Connection Pool Settings (via AppConfig):
    - pool_size: Number of connections to keep open
    - max_overflow: Max additional connections when pool is full
    - pool_timeout: Seconds to wait for connection from pool
    - pool_recycle: Seconds before recycling connections

Usage:
    # FastAPI dependency injection
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    
    # Context manager
    with get_db_context() as db:
        user = db.query(User).first()
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, inspect, pool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from core.settings import get_app_config
from utils.log import log_debug, log_error, log_info, log_success

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine with connection pooling."""
    global _engine
    if _engine is None:
        config = get_app_config()
        
        log_info(f"Creating database engine with URL: {config.database_url.split('@')[-1]}")
        
        # Create engine with connection pooling
        connect_args = {}
        if getattr(config, "database_statement_timeout_ms", 0) > 0:
            connect_args["options"] = f"-c statement_timeout={config.database_statement_timeout_ms}"
        if getattr(config, "database_application_name", None):
            connect_args["application_name"] = config.database_application_name

        _engine = create_engine(
            config.database_url,
            echo=config.database_echo,
            pool_size=config.database_pool_size,
            max_overflow=config.database_max_overflow,
            pool_timeout=config.database_pool_timeout,
            pool_recycle=config.database_pool_recycle,
            pool_pre_ping=True,
            pool_use_lifo=True,
            connect_args=connect_args,
        )
        
        # Add connection event listeners for logging
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            log_debug("Database connection established")
        
        @event.listens_for(_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            log_debug("Database connection closed")
        
        log_success("Database engine created successfully")

        # Ensure core tables exist (dev-friendly bootstrap)
        if getattr(config, "enable_db_autocreate", False):
            try:
                inspector = inspect(_engine)
                if not inspector.has_table("user"):
                    log_info("Database tables missing. Initializing schema...")
                    from models.base import Base
                    from models import (
                        user,
                        thread,
                        message,
                        user_profile,
                        audit_log,
                    )
                    Base.metadata.create_all(bind=_engine)
                    log_success("Database schema initialized")
            except Exception as e:
                log_error(f"Database schema check failed: {e}")
    
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
        log_debug("Session factory created")
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session.
    
    Yields:
        Session: Database session instance
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        log_debug("Database session created")
        yield db
        db.commit()
        log_debug("Database session committed")
    except SQLAlchemyError as e:
        log_error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        log_debug("Database session closed")


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database session.
    
    Yields:
        Session: Database session instance
        
    Example:
        ```python
        with get_db_context() as db:
            user = db.query(User).first()
        ```
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        log_debug("Database context session created")
        yield db
        db.commit()
        log_debug("Database context session committed")
    except SQLAlchemyError as e:
        log_error(f"Database context session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        log_debug("Database context session closed")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database session (streamlit-friendly alias).

    Yields:
        Session: Database session instance
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        log_debug("Database session created")
        yield db
        db.commit()
        log_debug("Database session committed")
    except SQLAlchemyError as e:
        log_error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        log_debug("Database session closed")


def init_db() -> None:
    """Initialize database tables.
    
    Note:
        This should only be used in development.
        In production, use Alembic migrations.
    """
    from models.base import Base
    # Import all models to register them with Base
    from models import (  # noqa: F401
        user,
        thread,
        message,
        user_profile,
        audit_log,
    )
    
    engine = get_engine()
    log_info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    log_success("Database tables created successfully")


def drop_db() -> None:
    """Drop all database tables.
    
    Warning:
        This will delete all data! Use with caution.
    """
    from models.base import Base
    from models import (  # noqa: F401
        user,
        thread,
        message,
        user_profile,
        audit_log,
    )
    
    engine = get_engine()
    log_info("Dropping database tables...")
    Base.metadata.drop_all(bind=engine)
    log_success("Database tables dropped successfully")
