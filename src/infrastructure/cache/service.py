"""Redis-backed cache and short-term memory service.

Design goals:
- Redis is a second layer over Postgres/Qdrant: always safe fallbacks.
- TTL-first: treat Redis as volatile by default.
- Minimal coupling: use redis_tool low-level primitives.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import redis as _redis

from infrastructure.cache.schemas import (
	CachedExtractResult,
	CachedRetrievalResult,
	CachedWebResult,
	HotMessage,
	Role,
	WarmConversationSummary,
)
from infrastructure.cache.utils import make_cache_key
from core.settings import get_redis_config
from infrastructure.cache.redis_cache import redis_tool, _CONN_ERRORS
from utils.log import log_debug, log_info, log_warning


class CacheService:
	def __init__(self) -> None:
		self._cfg = get_redis_config()

	# Hot conversation
	def append_hot_message(self, *, thread_id: str, role: Role, content: str) -> None:
		if not thread_id or not content:
			return
		key = redis_tool._key("hot", thread_id)
		try:
			msg = HotMessage(role=role, content=content)
			payload = msg.model_dump_json().encode("utf-8")
			client = redis_tool.client()
			client.rpush(key, payload)
			max_messages = self._cfg.hot_conversation_max_messages
			if max_messages > 0:
				client.ltrim(key, -max_messages, -1)
			client.expire(key, self._cfg.hot_conversation_ttl_seconds)
		except _CONN_ERRORS as e:
			log_warning(f"Redis unavailable (hot append): {e}")
		except Exception as e:
			log_warning(f"Redis hot append failed: {e}")

	def get_hot_messages(self, *, thread_id: str) -> List[HotMessage]:
		if not thread_id:
			return []
		key = redis_tool._key("hot", thread_id)
		try:
			raw_items = redis_tool.client().lrange(key, 0, -1) or []
			items: List[HotMessage] = []
			for raw in raw_items:
				try:
					items.append(HotMessage.model_validate_json(raw.decode("utf-8")))
				except Exception:
					continue
			return items
		except _CONN_ERRORS:
			return []
		except Exception as e:
			log_warning(f"Redis hot read failed: {e}")
			return []

	# Warm summaries
	def set_warm_summary(self, *, thread_id: str, summary: str, ttl_seconds: Optional[int] = None) -> None:
		if not thread_id or not summary:
			return
		key = redis_tool._key("warm_summary", thread_id)
		try:
			obj = WarmConversationSummary(thread_id=thread_id, summary=summary)
			exp = int(ttl_seconds or self._cfg.warm_summary_ttl_seconds)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except _CONN_ERRORS as e:
			log_warning(f"Redis unavailable (warm summary set): {e}")
		except Exception as e:
			log_warning(f"Redis warm summary set failed: {e}")

	def get_warm_summary(self, *, thread_id: str) -> Optional[WarmConversationSummary]:
		if not thread_id:
			return None
		key = redis_tool._key("warm_summary", thread_id)
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return WarmConversationSummary.model_validate_json(raw.decode("utf-8"))
		except _CONN_ERRORS:
			return None
		except Exception as e:
			log_warning(f"Redis warm summary read failed: {e}")
			return None

	# Tool dedup
	def mark_tool_call(self, *, tool_name: str, params: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
		"""Return True if this call is NEW within TTL; False if duplicate."""
		exp = int(ttl_seconds or self._cfg.tool_dedup_ttl_seconds)
		key = make_cache_key(prefix=redis_tool._key("tool_dedup", tool_name), parts={"tool": tool_name, "params": params})
		try:
			ok = redis_tool.client().set(key, b"1", nx=True, ex=exp)
			return bool(ok)
		except _CONN_ERRORS:
			return True
		except Exception as e:
			log_warning(f"Redis tool dedup failed: {e}")
			return True

	# Web search cache
	def get_web_cache(self, *, query: str, params: Dict[str, Any]) -> Optional[CachedWebResult]:
		key = make_cache_key(prefix=redis_tool._key("web", "cache"), parts={"query": query, "params": params})
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return CachedWebResult.model_validate_json(raw.decode("utf-8"))
		except _CONN_ERRORS:
			return None
		except Exception as e:
			log_warning(f"Redis web cache read failed: {e}")
			return None

	def set_web_cache(self, *, query: str, params: Dict[str, Any], result: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
		exp = int(ttl_seconds or self._cfg.web_cache_ttl_seconds)
		key = make_cache_key(prefix=redis_tool._key("web", "cache"), parts={"query": query, "params": params})
		try:
			obj = CachedWebResult(query=query, params=params, result=result)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except _CONN_ERRORS as e:
			log_warning(f"Redis unavailable (web cache set): {e}")
		except Exception as e:
			log_warning(f"Redis web cache set failed: {e}")

	# Extract cache
	def get_extract_cache(self, *, urls: List[str], params: Dict[str, Any]) -> Optional[CachedExtractResult]:
		key = make_cache_key(prefix=redis_tool._key("extract", "cache"), parts={"urls": sorted(urls), "params": params})
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return CachedExtractResult.model_validate_json(raw.decode("utf-8"))
		except _CONN_ERRORS:
			return None
		except Exception as e:
			log_warning(f"Redis extract cache read failed: {e}")
			return None

	def set_extract_cache(self, *, urls: List[str], params: Dict[str, Any], result: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
		exp = int(ttl_seconds or self._cfg.extract_cache_ttl_seconds)
		key = make_cache_key(prefix=redis_tool._key("extract", "cache"), parts={"urls": sorted(urls), "params": params})
		try:
			obj = CachedExtractResult(urls=sorted(urls), params=params, result=result)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except _CONN_ERRORS as e:
			log_warning(f"Redis unavailable (extract cache set): {e}")
		except Exception as e:
			log_warning(f"Redis extract cache set failed: {e}")

	# Retrieval cache
	def get_retrieval_cache(self, *, query: str, k: int) -> Optional[CachedRetrievalResult]:
		key = make_cache_key(prefix=redis_tool._key("retrieval", "cache"), parts={"query": query, "k": int(k)})
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return CachedRetrievalResult.model_validate_json(raw.decode("utf-8"))
		except _CONN_ERRORS:
			return None
		except Exception as e:
			log_warning(f"Redis retrieval cache read failed: {e}")
			return None

	def set_retrieval_cache(self, *, query: str, k: int, result_text: str, ttl_seconds: Optional[int] = None) -> None:
		exp = int(ttl_seconds or self._cfg.retrieval_cache_ttl_seconds)
		key = make_cache_key(prefix=redis_tool._key("retrieval", "cache"), parts={"query": query, "k": int(k)})
		try:
			obj = CachedRetrievalResult(query=query, k=int(k), result_text=result_text)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except _CONN_ERRORS as e:
			log_warning(f"Redis unavailable (retrieval cache set): {e}")
		except Exception as e:
			log_warning(f"Redis retrieval cache set failed: {e}")


	_NS_USER = "user"
	_NS_DASHBOARD = "dashboard"
	_NS_THREADS = "threads"
	_NS_XP = "xp"
	_NS_MISSION_STATS = "mission_stats"


	def get_cached_user(self, user_id: str) -> Optional[Dict[str, Any]]:
		"""Load a cached user dict (id, username, email, role)."""
		return redis_tool.cache_get_json(namespace=self._NS_USER, key=user_id)

	def set_cached_user(self, user_id: str, user_data: Dict[str, Any]) -> None:
		"""Cache minimal user data after a Postgres lookup."""
		redis_tool.cache_set_json(
			namespace=self._NS_USER, key=user_id,
			value=user_data, ttl_seconds=self._cfg.user_cache_ttl_seconds,
		)

	def invalidate_user(self, user_id: str) -> None:
		"""Evict the cached user (on role change, password reset, etc.)."""
		redis_tool.cache_delete(namespace=self._NS_USER, key=user_id)


	def get_cached_dashboard(self, user_id: str) -> Optional[Dict[str, Any]]:
		return redis_tool.cache_get_json(namespace=self._NS_DASHBOARD, key=user_id)

	def set_cached_dashboard(self, user_id: str, data: Dict[str, Any]) -> None:
		redis_tool.cache_set_json(
			namespace=self._NS_DASHBOARD, key=user_id,
			value=data, ttl_seconds=self._cfg.dashboard_cache_ttl_seconds,
		)

	def invalidate_dashboard(self, user_id: str) -> None:
		redis_tool.cache_delete(namespace=self._NS_DASHBOARD, key=user_id)


	def get_cached_threads(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
		return redis_tool.cache_get_json(namespace=self._NS_THREADS, key=user_id)

	def set_cached_threads(self, user_id: str, data: List[Dict[str, Any]]) -> None:
		redis_tool.cache_set_json(
			namespace=self._NS_THREADS, key=user_id,
			value=data, ttl_seconds=self._cfg.thread_list_cache_ttl_seconds,
		)

	def invalidate_threads(self, user_id: str) -> None:
		redis_tool.cache_delete(namespace=self._NS_THREADS, key=user_id)


	def get_cached_xp(self, user_id: str) -> Optional[int]:
		return redis_tool.cache_get_json(namespace=self._NS_XP, key=user_id)

	def set_cached_xp(self, user_id: str, xp: int) -> None:
		redis_tool.cache_set_json(
			namespace=self._NS_XP, key=user_id,
			value=xp, ttl_seconds=self._cfg.xp_cache_ttl_seconds,
		)

	def invalidate_xp(self, user_id: str) -> None:
		redis_tool.cache_delete(namespace=self._NS_XP, key=user_id)


	def get_cached_mission_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
		return redis_tool.cache_get_json(namespace=self._NS_MISSION_STATS, key=user_id)

	def set_cached_mission_stats(self, user_id: str, data: Dict[str, Any]) -> None:
		redis_tool.cache_set_json(
			namespace=self._NS_MISSION_STATS, key=user_id,
			value=data, ttl_seconds=self._cfg.mission_stats_cache_ttl_seconds,
		)

	def invalidate_mission_stats(self, user_id: str) -> None:
		redis_tool.cache_delete(namespace=self._NS_MISSION_STATS, key=user_id)


	def health(self) -> Dict[str, Any]:
		ok = redis_tool.ping()
		cfg = self._cfg
		return {
			"redis_ok": bool(ok),
			"host": cfg.host,
			"port": cfg.port,
			"db": cfg.db,
			"key_prefix": cfg.key_prefix,
		}

	def clear_thread_cache(self, *, thread_id: str) -> Dict[str, bool]:
		"""Clear all cached data for a specific thread."""
		if not thread_id:
			return {"error": "thread_id required"}

		results = {
			"hot_messages": False,
			"warm_summary": False,
			"graph_state": False,
		}

		try:
			client = redis_tool.client()
		except _CONN_ERRORS:
			log_warning("Redis unavailable; cannot clear thread cache")
			return results

		try:
			results["hot_messages"] = bool(client.delete(redis_tool._key("hot", thread_id)))
		except Exception as e:
			log_warning(f"Failed to clear hot messages: {e}")

		try:
			results["warm_summary"] = bool(client.delete(redis_tool._key("warm_summary", thread_id)))
		except Exception as e:
			log_warning(f"Failed to clear warm summary: {e}")

		try:
			results["graph_state"] = redis_tool.delete_graph_state(thread_id=thread_id)
		except Exception as e:
			log_warning(f"Failed to clear graph state: {e}")

		log_info(f"Cleared thread cache for {thread_id}: {results}")
		return results


cache_service = CacheService()
