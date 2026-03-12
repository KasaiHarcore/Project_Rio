"""
Configuration Management for Agent
Centralized configuration: CLI / Web interfaces
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote_plus

# =============================================================================
# Workflow Constants
# =============================================================================

# Preview length for tool outputs in traces
TOOL_PREVIEW_LENGTH = 500

# Default maximum iterations for supervisor
DEFAULT_MAX_ITERATIONS = 10

# Default checkpoint namespace
DEFAULT_CHECKPOINT_NS = "thread"

# Worker timeouts (in seconds)
WORKER_TIMEOUT_SECONDS = 60

# Supervisor prompt limits
MAX_CONTEXT_LENGTH = 8000
MAX_RESPONSE_LENGTH = 4000

# Streaming batch sizes
STREAM_TOKEN_BATCH_SIZE = 3

# Human-in-the-loop timeout (in seconds)
HUMAN_INTERRUPT_TIMEOUT = 3600

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0
RETRY_BACKOFF_MAX = 10.0

def _env_bool(key: str, default: str = "False") -> bool:
	return os.getenv(key, default).lower() == "true"


def _env_int(key: str, default: str) -> int:
	return int(os.getenv(key, default))


def _env_float(key: str, default: str) -> float:
	return float(os.getenv(key, default))


def _env_str(key: str, default: Optional[str] = None) -> Optional[str]:
	value = os.getenv(key)
	if value is None:
		return default
	value = value.strip()
	return value if value else default


@dataclass
class AgentConfig:
	"""Agent execution configuration"""

	mode: Literal["rag", "web", "chat", "sql"] = "chat"
	user_role: Literal["user", "admin"] = "user"
	character: str = "rio"  # Persona ID: "rio", etc.
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
	enable_reflection: bool = True  # Note: Reflection is now integrated into supervisor routing
	enable_persistence: bool = True
	web_search_max_calls: int = 6
	web_search_max_results: int = 5
	web_search_dedupe: bool = True
	retrieval_strategy: Literal["standard", "hyde", "rewrite"] = "standard"

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

		# SQL mode requires admin role
		if self.mode == "sql" and self.user_role != "admin":
			raise ValueError("SQL mode is restricted to admin users only")

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

		if self.retrieval_strategy not in {"standard", "hyde", "rewrite"}:
			raise ValueError(
				f"Invalid retrieval_strategy: {self.retrieval_strategy}. "
				"Must be one of: standard, hyde, rewrite"
			)


@dataclass
class VectorDBConfig:
	"""Vector database configuration"""

	persist_dir: str = "./storage/qdrant"
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
			persist_dir=_env_str("QDRANT_PATH", "./storage/qdrant"),
			collection_name=_env_str("QDRANT_COLLECTION", "rag-fpt"),
			embedding_model=_env_str("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
			sparse_embedding_model=_env_str("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25"),
			chunk_size=_env_int("CHUNK_SIZE", "1000"),
			chunk_overlap=_env_int("CHUNK_OVERLAP", "200"),
			threshold=_env_float("THRESHOLD", "0.7"),
			retrieval_score_threshold=(
				float(retrieval_score_threshold)
				if retrieval_score_threshold is not None
				and retrieval_score_threshold.strip() != ""
				else None
			),
			vector_db_autocreate=_env_bool("VECTORDB_AUTOCREATE", "True"),
			vector_db_eager_init=_env_bool("VECTORDB_EAGER_INIT", "True"),
		)


@dataclass
class RedisConfig:
	"""Redis configuration (cache + working memory)."""

	host: str = "localhost"
	port: int = 6379
	db: int = 0
	username: Optional[str] = None
	password: Optional[str] = None
	ssl: bool = False

	# Connection behavior
	socket_timeout_seconds: float = 2.0
	socket_connect_timeout_seconds: float = 2.0
	health_check_interval_seconds: int = 30

	# Keying / TTLs
	key_prefix: str = "ai-agent"
	graph_state_ttl_seconds: int = 3600

	# Hot / warm memory
	hot_conversation_ttl_seconds: int = 6 * 3600
	hot_conversation_max_messages: int = 200
	warm_summary_ttl_seconds: int = 7 * 86400

	# Entity L2 cache TTLs
	user_cache_ttl_seconds: int = 300            # 5 min
	dashboard_cache_ttl_seconds: int = 60        # 1 min
	thread_list_cache_ttl_seconds: int = 120     # 2 min
	xp_cache_ttl_seconds: int = 600              # 10 min
	mission_stats_cache_ttl_seconds: int = 300   # 5 min

	# Tool/result caches
	tool_dedup_ttl_seconds: int = 600
	retrieval_cache_ttl_seconds: int = 1800
	web_cache_ttl_seconds: int = 900

	# LLM cache
	enable_llm_cache: bool = True
	llm_cache_ttl_seconds: int = 86400

	def __post_init__(self):
		if self.port <= 0 or self.port > 65535:
			raise ValueError("redis port must be in [1, 65535]")
		if self.db < 0:
			raise ValueError("redis db must be >= 0")
		if self.socket_timeout_seconds <= 0:
			raise ValueError("redis socket_timeout_seconds must be > 0")
		if self.socket_connect_timeout_seconds <= 0:
			raise ValueError("redis socket_connect_timeout_seconds must be > 0")
		if self.graph_state_ttl_seconds <= 0:
			raise ValueError("redis graph_state_ttl_seconds must be > 0")
		if self.hot_conversation_ttl_seconds <= 0:
			raise ValueError("redis hot_conversation_ttl_seconds must be > 0")
		if self.hot_conversation_max_messages < 0:
			raise ValueError("redis hot_conversation_max_messages must be >= 0")
		if self.warm_summary_ttl_seconds <= 0:
			raise ValueError("redis warm_summary_ttl_seconds must be > 0")
		if self.tool_dedup_ttl_seconds <= 0:
			raise ValueError("redis tool_dedup_ttl_seconds must be > 0")
		if self.retrieval_cache_ttl_seconds <= 0:
			raise ValueError("redis retrieval_cache_ttl_seconds must be > 0")
		if self.web_cache_ttl_seconds <= 0:
			raise ValueError("redis web_cache_ttl_seconds must be > 0")
		if self.llm_cache_ttl_seconds <= 0:
			raise ValueError("redis llm_cache_ttl_seconds must be > 0")
  
	@classmethod
	def from_env(cls) -> "RedisConfig":
		"""Create configuration from environment variables."""
		return cls(
			host=_env_str("REDIS_HOST", "localhost"),
			port=_env_int("REDIS_PORT", "6379"),
			db=_env_int("REDIS_DB", "0"),
			username=_env_str("REDIS_USER"),
			password=_env_str("REDIS_PASSWORD"),
			ssl=_env_bool("REDIS_SSL", "False"),
			socket_timeout_seconds=_env_float("REDIS_SOCKET_TIMEOUT", "2.0"),
			socket_connect_timeout_seconds=_env_float("REDIS_SOCKET_CONNECT_TIMEOUT", "2.0"),
			health_check_interval_seconds=_env_int("REDIS_HEALTH_CHECK_INTERVAL", "30"),
			key_prefix=_env_str("REDIS_KEY_PREFIX", "ai-agent"),
			graph_state_ttl_seconds=_env_int("REDIS_GRAPH_STATE_TTL", "3600"),
			hot_conversation_ttl_seconds=_env_int("REDIS_HOT_TTL", str(6 * 3600)),
			hot_conversation_max_messages=_env_int("REDIS_HOT_MAX_MESSAGES", "200"),
			warm_summary_ttl_seconds=_env_int("REDIS_WARM_SUMMARY_TTL", str(7 * 86400)),
			user_cache_ttl_seconds=_env_int("REDIS_USER_CACHE_TTL", "300"),
			dashboard_cache_ttl_seconds=_env_int("REDIS_DASHBOARD_CACHE_TTL", "60"),
			thread_list_cache_ttl_seconds=_env_int("REDIS_THREAD_LIST_CACHE_TTL", "120"),
			xp_cache_ttl_seconds=_env_int("REDIS_XP_CACHE_TTL", "600"),
			mission_stats_cache_ttl_seconds=_env_int("REDIS_MISSION_STATS_CACHE_TTL", "300"),
			tool_dedup_ttl_seconds=_env_int("REDIS_TOOL_DEDUP_TTL", "600"),
			retrieval_cache_ttl_seconds=_env_int("REDIS_RETRIEVAL_CACHE_TTL", "1800"),
			web_cache_ttl_seconds=_env_int("REDIS_WEB_CACHE_TTL", "900"),
			enable_llm_cache=_env_bool("REDIS_ENABLE_LLM_CACHE", "True"),
			llm_cache_ttl_seconds=_env_int("REDIS_LLM_CACHE_TTL", "86400"),
		)


@dataclass
class Neo4jConfig:
	"""Neo4j graph database configuration."""

	uri: str = "bolt://localhost:7687"
	username: str = "neo4j"
	password: str = "password"
	database: str = "neo4j"
	enabled: bool = False  # opt-in, no breaking change

	@classmethod
	def from_env(cls) -> "Neo4jConfig":
		"""Create configuration from environment variables."""
		return cls(
			uri=_env_str("NEO4J_URI", "bolt://localhost:7687"),
			username=_env_str("NEO4J_USERNAME", "neo4j"),
			password=_env_str("NEO4J_PASSWORD", "password"),
			database=_env_str("NEO4J_DATABASE", "neo4j"),
			enabled=_env_bool("NEO4J_ENABLED", "False"),
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
	database_pool_size: int = 20
	database_max_overflow: int = 20
	database_pool_timeout: int = 30
	database_pool_recycle: int = 3600
	database_statement_timeout_ms: int = 0
	database_application_name: str = "ai-agent"

	# Paths
	storage_dir: str = "./storage"
	docs_dir: str = "./docs"

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
			openai_api_key=_env_str("OPENAI_API_KEY"),
			openrouter_api_key=_env_str("OPENROUTER_API_KEY"),
			tavily_api_key=_env_str("TAVILY_API_KEY"),
			database_url=database_url,
			database_echo=_env_bool("DATABASE_ECHO", "False"),
			database_pool_size=_env_int("DATABASE_POOL_SIZE", "20"),
			database_max_overflow=_env_int("DATABASE_MAX_OVERFLOW", "20"),
			database_pool_timeout=_env_int("DATABASE_POOL_TIMEOUT", "30"),
			database_pool_recycle=_env_int("DATABASE_POOL_RECYCLE", "3600"),
			database_statement_timeout_ms=_env_int("DATABASE_STATEMENT_TIMEOUT_MS", "0"),
			database_application_name=_env_str("DATABASE_APPLICATION_NAME", "ai-agent"),
			storage_dir=_env_str("STORAGE_DIR", "./storage"),
			docs_dir=_env_str("DOCS_DIR", "./docs"),
			log_level=_env_str("LOG_LEVEL", "INFO"),
			enable_db_autocreate=_env_bool("ENABLE_DB_AUTOCREATE", "True"),
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


# =============================================================================
# OAuth2 Configuration
# =============================================================================

@dataclass
class OAuthConfig:
	"""OAuth2 provider configuration (Google + GitHub)."""

	google_client_id: Optional[str] = None
	google_client_secret: Optional[str] = None
	github_client_id: Optional[str] = None
	github_client_secret: Optional[str] = None
	redirect_base_url: str = "http://localhost:3000"

	# OIDC settings
	google_oidc_enabled: bool = True
	oidc_jwks_cache_ttl: int = 3600

	@property
	def google_enabled(self) -> bool:
		return bool(self.google_client_id and self.google_client_secret)

	@property
	def github_enabled(self) -> bool:
		return bool(self.github_client_id and self.github_client_secret)

	@classmethod
	def from_env(cls) -> "OAuthConfig":
		return cls(
			google_client_id=_env_str("GOOGLE_CLIENT_ID"),
			google_client_secret=_env_str("GOOGLE_CLIENT_SECRET"),
			github_client_id=_env_str("GITHUB_CLIENT_ID"),
			github_client_secret=_env_str("GITHUB_CLIENT_SECRET"),
			redirect_base_url=_env_str("OAUTH_REDIRECT_BASE_URL", "http://localhost:3000"),
			google_oidc_enabled=_env_bool("GOOGLE_OIDC_ENABLED", "True"),
			oidc_jwks_cache_ttl=_env_int("OIDC_JWKS_CACHE_TTL", "3600"),
		)


# =============================================================================
# CORS Configuration
# =============================================================================

@dataclass
class CorsConfig:
	"""CORS configuration with environment-driven whitelist."""

	allowed_origins: list[str] | None = None
	allow_credentials: bool = True
	allowed_methods: list[str] | None = None
	allowed_headers: list[str] | None = None
	max_age: int = 600  # preflight cache in seconds (10 min)

	def __post_init__(self):
		if self.allowed_origins is None:
			self.allowed_origins = [
				"http://localhost:3000",
				"http://127.0.0.1:3000",
				"http://localhost:3001",
			]
		if self.allowed_methods is None:
			self.allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
		if self.allowed_headers is None:
			self.allowed_headers = [
				"Authorization",
				"Content-Type",
				"Accept",
				"X-Request-Id",
				"X-Thread-Id",
			]

	@classmethod
	def from_env(cls) -> "CorsConfig":
		origins_raw = _env_str("CORS_ORIGINS")
		origins = (
			[o.strip() for o in origins_raw.split(",") if o.strip()]
			if origins_raw
			else None
		)
		methods_raw = _env_str("CORS_METHODS")
		methods = (
			[m.strip() for m in methods_raw.split(",") if m.strip()]
			if methods_raw
			else None
		)
		headers_raw = _env_str("CORS_HEADERS")
		headers = (
			[h.strip() for h in headers_raw.split(",") if h.strip()]
			if headers_raw
			else None
		)
		return cls(
			allowed_origins=origins,
			allow_credentials=_env_bool("CORS_ALLOW_CREDENTIALS", "True"),
			allowed_methods=methods,
			allowed_headers=headers,
			max_age=_env_int("CORS_MAX_AGE", "600"),
		)


# =============================================================================
# Concurrency Configuration
# =============================================================================

@dataclass
class ConcurrencyConfig:
	"""Thread / process pool sizes for the ConcurrencyManager."""

	thread_pool_size: int = 32
	process_pool_size: int = 2

	def __post_init__(self):
		if self.thread_pool_size < 1:
			raise ValueError("thread_pool_size must be >= 1")
		if self.process_pool_size < 1:
			raise ValueError("process_pool_size must be >= 1")

	@classmethod
	def from_env(cls) -> "ConcurrencyConfig":
		return cls(
			thread_pool_size=_env_int("THREAD_POOL_SIZE", "32"),
			process_pool_size=_env_int("PROCESS_POOL_SIZE", "2"),
		)


# =============================================================================
# Global configuration instances
# =============================================================================

_app_config: Optional[AppConfig] = None
_vectordb_config: Optional[VectorDBConfig] = None
_redis_config: Optional[RedisConfig] = None
_oauth_config: Optional[OAuthConfig] = None
_cors_config: Optional[CorsConfig] = None
_neo4j_config: Optional[Neo4jConfig] = None
_concurrency_config: Optional[ConcurrencyConfig] = None
_dotenv_loaded: bool = False


def _ensure_dotenv() -> None:
	"""Load .env from the repo root exactly once.

	This is called automatically by every ``get_*_config()`` factory so that
	environment variables are available no matter which entry point starts the
	process (main.py serve, main.py api, uvicorn --reload workers, alembic,
	tests, etc.).
	"""
	global _dotenv_loaded
	if _dotenv_loaded:
		return
	try:
		from dotenv import load_dotenv
		# Walk up from  src/core/settings.py  →  src/  →  repo root
		repo_root = Path(__file__).resolve().parents[2]
		env_file = repo_root / ".env"
		if env_file.is_file():
			load_dotenv(env_file, override=False)
	except ImportError:
		pass  # python-dotenv not installed – rely on real env vars
	_dotenv_loaded = True


def get_app_config() -> AppConfig:
	"""Get or create application configuration"""
	global _app_config
	if _app_config is None:
		_ensure_dotenv()
		_app_config = AppConfig.from_env()
	return _app_config


def get_vectordb_config() -> VectorDBConfig:
	"""Get or create vector database configuration"""
	global _vectordb_config
	if _vectordb_config is None:
		_ensure_dotenv()
		_vectordb_config = VectorDBConfig.from_env()
	return _vectordb_config


def get_redis_config() -> RedisConfig:
	"""Get or create Redis configuration."""
	global _redis_config
	if _redis_config is None:
		_ensure_dotenv()
		_redis_config = RedisConfig.from_env()
	return _redis_config


def get_oauth_config() -> OAuthConfig:
	"""Get or create OAuth2 configuration."""
	global _oauth_config
	if _oauth_config is None:
		_ensure_dotenv()
		_oauth_config = OAuthConfig.from_env()
	return _oauth_config


def get_cors_config() -> CorsConfig:
	"""Get or create CORS configuration."""
	global _cors_config
	if _cors_config is None:
		_ensure_dotenv()
		_cors_config = CorsConfig.from_env()
	return _cors_config


def get_neo4j_config() -> Neo4jConfig:
	"""Get or create Neo4j configuration."""
	global _neo4j_config
	if _neo4j_config is None:
		_ensure_dotenv()
		_neo4j_config = Neo4jConfig.from_env()
	return _neo4j_config


def get_concurrency_config() -> ConcurrencyConfig:
	"""Get or create concurrency configuration."""
	global _concurrency_config
	if _concurrency_config is None:
		_ensure_dotenv()
		_concurrency_config = ConcurrencyConfig.from_env()
	return _concurrency_config
