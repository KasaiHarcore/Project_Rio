"""Redis utilities: LangChain LLM cache + working-memory state store.

Notes:
- We intentionally use the default RedisCache (exact cache). Semantic caching
	can cause incorrect cache hits and make the agent appear "stuck".
- This module is intentionally lazy: it does not require Redis to be reachable
	at import time.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional

import redis

from langchain_core.globals import set_llm_cache
from langchain_redis import RedisCache
from langchain_core.messages import messages_from_dict, messages_to_dict

from core.settings import get_redis_config
from utils.log import log_debug, log_info, log_success, log_warning


class RedisTool:
	"""Thin Redis wrapper for caching and fast state persistence."""

	def __init__(self) -> None:
		self._config = get_redis_config()
		self._pool: Optional[redis.ConnectionPool] = None
		self._client: Optional[redis.Redis] = None

	def _build_pool(self) -> redis.ConnectionPool:
		cfg = self._config
		kwargs: Dict[str, Any] = {
			"host": cfg.host,
			"port": cfg.port,
			"db": cfg.db,
			"username": cfg.username,
			"password": cfg.password,
			"socket_timeout": cfg.socket_timeout_seconds,
			"socket_connect_timeout": cfg.socket_connect_timeout_seconds,
			"health_check_interval": cfg.health_check_interval_seconds,
			"retry_on_timeout": True,
			"decode_responses": False,
		}
		if cfg.ssl:
			kwargs["connection_class"] = redis.SSLConnection
		try:
			return redis.ConnectionPool(**kwargs)
		except TypeError:
			# Some redis-py combinations may not support username/health_check_interval.
			kwargs.pop("username", None)
			kwargs.pop("health_check_interval", None)
			return redis.ConnectionPool(**kwargs)

	def client(self) -> redis.Redis:
		"""Return a reusable Redis client."""
		if self._client is None:
			if self._pool is None:
				self._pool = self._build_pool()
			self._client = redis.Redis(connection_pool=self._pool)
		return self._client

	def ping(self) -> bool:
		"""Check Redis connectivity."""
		try:
			return bool(self.client().ping())
		except Exception as e:
			log_warning(f"Redis ping failed: {e}")
			return False

	def _redis_url(self) -> str:
		"""Build a redis:// URL for components that require it."""
		cfg = self._config
		scheme = "rediss" if cfg.ssl else "redis"
		creds = ""
		# username/password are optional for new installs.
		if cfg.username and cfg.password:
			creds = f"{cfg.username}:{cfg.password}@"
		elif cfg.password and not cfg.username:
			creds = f":{cfg.password}@"
		elif cfg.username and not cfg.password:
			creds = f"{cfg.username}@"
		return f"{scheme}://{creds}{cfg.host}:{cfg.port}/{cfg.db}"

	def enable_llm_cache(self) -> None:
		"""Enable LangChain LLM caching using RedisCache (exact cache)."""
		cfg = self._config
		if not cfg.enable_llm_cache:
			log_info("Redis LLM cache disabled by configuration")
			return

		if not self.ping():
			log_warning("Redis unavailable; skipping LLM cache setup")
			return

		try:
			prefix = f"{(cfg.key_prefix or 'ai-agent').strip(':')}:llm"
			cache = RedisCache(
				redis_url=self._redis_url(),
				ttl=int(cfg.llm_cache_ttl_seconds),
				prefix=prefix,
			)
			set_llm_cache(cache)
			log_success(f"Enabled Redis LLM cache via RedisCache (ttl={cfg.llm_cache_ttl_seconds}s)")
		except Exception as e:
			log_warning(f"Failed to enable Redis LLM cache: {e}")

	# --- Working memory: LangGraph state snapshots (fast, TTL) ---
	def _key(self, kind: str, id_: str) -> str:
		prefix = (self._config.key_prefix or "ai-agent").strip(":")
		return f"{prefix}:{kind}:{id_}"

	def cache_set_json(
		self,
		*,
		namespace: str,
		key: str,
		value: Any,
		ttl_seconds: int,
	) -> bool:
		"""Store a JSON-serializable value with TTL.

		This is a safe building block for caching Postgres-derived lookups in Redis.
		"""
		if not self.ping():
			return False
		redis_key = self._key(namespace, key)
		try:
			raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
			return bool(self.client().set(redis_key, raw, ex=int(ttl_seconds)))
		except Exception as e:
			log_warning(f"Failed to cache JSON value in Redis: {e}")
			return False

	def cache_get_json(self, *, namespace: str, key: str) -> Optional[Any]:
		"""Load a cached JSON value."""
		if not self.ping():
			return None
		redis_key = self._key(namespace, key)
		try:
			raw = self.client().get(redis_key)
			if not raw:
				return None
			return json.loads(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Failed to read cached JSON value from Redis: {e}")
			return None

	def save_graph_state(
		self,
		*,
		thread_id: str,
		state: Dict[str, Any],
		ttl_seconds: Optional[int] = None,
	) -> None:
		"""Persist a minimal `GraphState` snapshot for quick resume.

		Stores:
		- schema_version
		- messages (serialized via messages_to_dict)
		"""
		if not thread_id:
			raise ValueError("thread_id is required")
		if not self.ping():
			log_warning("Redis unavailable; skipping graph state save")
			return

		payload: Dict[str, Any] = {
			"schema_version": state.get("schema_version"),
			"messages": messages_to_dict(state.get("messages") or []),
		}
		raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		key = self._key("graph_state", str(thread_id))
		expire = int(ttl_seconds or self._config.graph_state_ttl_seconds)
		try:
			self.client().set(name=key, value=raw, ex=expire)
			log_debug(f"Saved graph state to Redis (thread_id={thread_id}, ttl={expire}s)")
		except Exception as e:
			log_warning(f"Failed to save graph state to Redis: {e}")

	def load_graph_state(self, *, thread_id: str) -> Optional[Dict[str, Any]]:
		"""Load the latest `GraphState` snapshot from Redis."""
		if not thread_id:
			raise ValueError("thread_id is required")
		if not self.ping():
			return None
		key = self._key("graph_state", str(thread_id))
		try:
			raw = self.client().get(key)
			if not raw:
				return None
			payload = json.loads(raw.decode("utf-8"))
			messages = messages_from_dict(payload.get("messages") or [])
			return {
				"schema_version": payload.get("schema_version"),
				"messages": messages,
			}
		except Exception as e:
			log_warning(f"Failed to load graph state from Redis: {e}")
			return None

	def delete_graph_state(self, *, thread_id: str) -> bool:
		"""Delete a Redis graph state snapshot."""
		if not thread_id:
			raise ValueError("thread_id is required")
		if not self.ping():
			return False
		key = self._key("graph_state", str(thread_id))
		try:
			return bool(self.client().delete(key))
		except Exception as e:
			log_warning(f"Failed to delete graph state from Redis: {e}")
			return False

	def get_config(self) -> Dict[str, Any]:
		"""Return current Redis configuration (safe, redacted)."""
		cfg = asdict(self._config)
		if cfg.get("password"):
			cfg["password"] = "***"
		return cfg


redis_tool = RedisTool()