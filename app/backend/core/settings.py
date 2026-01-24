"""
Configuration Management for FPT Policy RAG Agent
Centralized configuration for CLI and Web interfaces
"""

import os
from urllib.parse import quote_plus
from typing import Optional, Literal
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
	"""Agent execution configuration"""

	mode: Literal["rag", "web", "chat", "sql"] = "chat"
	user_role: Literal["user", "admin"] = "user"
	top_k: int = 5
	model_name: Optional[str] = None
	verify_max_retries: int = 2
	state_schema_version: int = 1
	checkpoint_every: int = 1
	state_scope: Literal["thread", "session", "user"] = "thread"
	max_execution_seconds: int = 120
	model_max_retries: int = 2
	model_backoff_base: float = 0.5
	model_backoff_max: float = 4.0
	history_max_items: int = 50
	enable_planner: bool = True
	enable_reflection: bool = True
	enable_persistence: bool = True
	web_search_max_calls: int = 6
	web_search_max_results: int = 5
	web_search_dedupe: bool = True

	def __post_init__(self):
		"""Validate configuration"""
		if self.top_k <= 0:
			raise ValueError("top_k must be greater than 0")

		if self.mode not in {"rag", "web", "chat", "sql"}:
			raise ValueError(
				f"Invalid mode: {self.mode}. Must be one of: rag, web, chat, sql"
			)

		if self.user_role not in {"user", "admin"}:
			raise ValueError("Invalid user_role: must be 'user' or 'admin'")

		if self.verify_max_retries < 0:
			raise ValueError("verify_max_retries must be >= 0")

		if self.state_schema_version <= 0:
			raise ValueError("state_schema_version must be >= 1")

		if self.checkpoint_every <= 0:
			raise ValueError("checkpoint_every must be >= 1")

		if self.max_execution_seconds <= 0:
			raise ValueError("max_execution_seconds must be >= 1")

		if self.model_max_retries < 0:
			raise ValueError("model_max_retries must be >= 0")

		if self.model_backoff_base <= 0:
			raise ValueError("model_backoff_base must be > 0")

		if self.model_backoff_max < self.model_backoff_base:
			raise ValueError("model_backoff_max must be >= model_backoff_base")

		if self.history_max_items < 0:
			raise ValueError("history_max_items must be >= 0")

		if self.web_search_max_calls < 0:
			raise ValueError("web_search_max_calls must be >= 0")

		if self.web_search_max_results < 1 or self.web_search_max_results > 20:
			raise ValueError("web_search_max_results must be in [1, 20]")


@dataclass
class VectorDBConfig:
	"""Vector database configuration"""

	persist_dir: str = "./app/storage/qdrant"
	collection_name: str = "rag-fpt"
	embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
	sparse_embedding_model: str = "Qdrant/bm25"
	chunk_size: int = 1000
	chunk_overlap: int = 200
	threshold: float = 0.7
	retrieval_score_threshold: Optional[float] = None
	vector_db_autocreate: bool = True
	vector_db_eager_init: bool = True

	@classmethod
	def from_env(cls) -> "VectorDBConfig":
		"""Create configuration from environment variables"""
		retrieval_score_threshold = os.getenv("VECTORDB_SCORE_THRESHOLD")
		return cls(
			persist_dir=os.getenv("QDRANT_PATH", "./app/storage/qdrant"),
			collection_name=os.getenv("QDRANT_COLLECTION", "rag-fpt"),
			embedding_model=os.getenv(
				"EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
			),
			sparse_embedding_model=os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25"),
			chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
			chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
			threshold=float(os.getenv("THRESHOLD", "0.7")),
			retrieval_score_threshold=(
				float(retrieval_score_threshold)
				if retrieval_score_threshold is not None
				and retrieval_score_threshold.strip() != ""
				else None
			),
			vector_db_autocreate=os.getenv("VECTORDB_AUTOCREATE", "True").lower() == "true",
			vector_db_eager_init=os.getenv("VECTORDB_EAGER_INIT", "True").lower() == "true",
		)


@dataclass
class AppConfig:
	"""Application-wide configuration"""

	# API Keys
	openai_api_key: Optional[str] = None
	openrouter_api_key: Optional[str] = None
	tavily_api_key: Optional[str] = None

	# Database Configuration
	database_url: str = None
	database_echo: bool = False
	database_pool_size: int = 5
	database_max_overflow: int = 10
	database_pool_timeout: int = 30
	database_pool_recycle: int = 3600
	database_statement_timeout_ms: int = 0
	database_application_name: str = "ai-agent"

	# Paths
	storage_dir: str = "./app/storage"
	docs_dir: str = "./app/docs"

	# Logging
	log_level: str = "INFO"

	# Workflow state retention
	# Database bootstrap (dev-only)
	enable_db_autocreate: bool = False

	@classmethod
	def from_env(cls) -> "AppConfig":
		"""Create configuration from environment variables"""
		database_url = os.getenv("DATABASE_URL")
		if not database_url:
			pg_host = os.getenv("PGHOST") or os.getenv("LOCAL_POSTGRES_WIN_HOST") or "localhost"
			pg_port = os.getenv("PGPORT") or os.getenv("LOCAL_POSTGRES_PORT") or "5432"
			pg_db = os.getenv("PGDATABASE") or os.getenv("LOCAL_POSTGRES_DB") or "rag_db"
			pg_user = os.getenv("PGUSER") or os.getenv("LOCAL_POSTGRES_USER") or "postgres"
			pg_password = os.getenv("PGPASSWORD") or os.getenv("LOCAL_POSTGRES_PASSWORD")

			if pg_password:
				pg_password = quote_plus(pg_password)
				database_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
			else:
				database_url = f"postgresql+psycopg2://{pg_user}@{pg_host}:{pg_port}/{pg_db}"

		return cls(
			openai_api_key=os.getenv("OPENAI_API_KEY"),
			openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
			tavily_api_key=os.getenv("TAVILY_API_KEY"),
			database_url=database_url,
			database_echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
			database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
			database_max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
			database_pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
			database_pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "3600")),
			database_statement_timeout_ms=int(os.getenv("DATABASE_STATEMENT_TIMEOUT_MS", "0")),
			database_application_name=os.getenv("DATABASE_APPLICATION_NAME", "ai-agent"),
			storage_dir=os.getenv("STORAGE_DIR", "./app/storage"),
			docs_dir=os.getenv("DOCS_DIR", "./app/docs"),
			log_level=os.getenv("LOG_LEVEL", "INFO"),
			enable_db_autocreate=os.getenv("ENABLE_DB_AUTOCREATE", "True").lower() == "true",
		)

	def validate(self) -> tuple[bool, list[str]]:
		"""Validate configuration"""
		errors = []

		if self.database_pool_size <= 0:
			errors.append("database_pool_size must be > 0")
		if self.database_max_overflow < 0:
			errors.append("database_max_overflow must be >= 0")
		if self.database_pool_timeout < 1:
			errors.append("database_pool_timeout must be >= 1")
		if self.database_pool_recycle < 0:
			errors.append("database_pool_recycle must be >= 0")
		if self.database_statement_timeout_ms < 0:
			errors.append("database_statement_timeout_ms must be >= 0")

		# Validate paths
		for path_name, path_value in [
			("storage_dir", self.storage_dir),
			("docs_dir", self.docs_dir),
		]:
			path = Path(path_value)
			try:
				path.mkdir(parents=True, exist_ok=True)
			except Exception as e:
				errors.append(f"Cannot create {path_name} at {path_value}: {e}")

		return len(errors) == 0, errors


# Global configuration instances
_app_config: Optional[AppConfig] = None
_vectordb_config: Optional[VectorDBConfig] = None


def get_app_config() -> AppConfig:
	"""Get or create application configuration"""
	global _app_config
	if _app_config is None:
		_app_config = AppConfig.from_env()
	return _app_config


def get_vectordb_config() -> VectorDBConfig:
	"""Get or create vector database configuration"""
	global _vectordb_config
	if _vectordb_config is None:
		_vectordb_config = VectorDBConfig.from_env()
	return _vectordb_config
