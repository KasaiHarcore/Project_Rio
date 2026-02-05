"""Redis-backed cache and short-term memory service.

Design goals:
- Redis is a second layer over Postgres/Qdrant: always safe fallbacks.
- TTL-first: treat Redis as volatile by default.
- Minimal coupling: use redis_tool low-level primitives.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.infrastructure.cache.schemas import (
	CachedRetrievalResult,
	CachedWebResult,
	HotMessage,
	Role,
	SessionState,
	UserShortTermMemory,
	WarmConversationSummary,
)
from backend.infrastructure.cache.utils import make_cache_key
from backend.core.settings import get_redis_config
from backend.infrastructure.integrations.tools.redis_tool import redis_tool
from backend.utils.log import log_debug, log_info, log_warning


class CacheService:
	def __init__(self) -> None:
		self._cfg = get_redis_config()

	# Hot conversation
	def append_hot_message(self, *, thread_id: str, role: Role, content: str) -> None:
		if not thread_id or not content:
			return
		if not redis_tool.ping():
			return

		key = redis_tool._key("hot", thread_id)
		try:
			msg = HotMessage(role=role, content=content)
			# Store as JSON lines in a list.
			payload = msg.model_dump_json().encode("utf-8")
			client = redis_tool.client()
			client.rpush(key, payload)
			# Keep last N messages.
			max_messages = int(getattr(self._cfg, "hot_conversation_max_messages", 200) or 200)
			if max_messages > 0:
				client.ltrim(key, -max_messages, -1)
			client.expire(key, int(getattr(self._cfg, "hot_conversation_ttl_seconds", 6 * 3600) or 21600))
		except Exception as e:
			log_warning(f"Redis hot append failed: {e}")

	def get_hot_messages(self, *, thread_id: str) -> List[HotMessage]:
		if not thread_id or not redis_tool.ping():
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
		except Exception as e:
			log_warning(f"Redis hot read failed: {e}")
			return []

	# Warm summaries
	def set_warm_summary(self, *, thread_id: str, summary: str, ttl_seconds: Optional[int] = None) -> None:
		if not thread_id or not summary:
			return
		if not redis_tool.ping():
			return
		key = redis_tool._key("warm_summary", thread_id)
		try:
			obj = WarmConversationSummary(thread_id=thread_id, summary=summary)
			exp = int(ttl_seconds or getattr(self._cfg, "warm_summary_ttl_seconds", 7 * 86400) or 604800)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except Exception as e:
			log_warning(f"Redis warm summary set failed: {e}")

	def get_warm_summary(self, *, thread_id: str) -> Optional[WarmConversationSummary]:
		if not thread_id or not redis_tool.ping():
			return None
		key = redis_tool._key("warm_summary", thread_id)
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return WarmConversationSummary.model_validate_json(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Redis warm summary read failed: {e}")
			return None


	# Session full state
	def set_session_state(self, *, session_id: str, state: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
		if not session_id:
			return
		if not redis_tool.ping():
			return
		key = redis_tool._key("session", session_id)
		try:
			obj = SessionState(session_id=session_id, state=state)
			exp = int(ttl_seconds or getattr(self._cfg, "session_state_ttl_seconds", 6 * 3600) or 21600)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except Exception as e:
			log_warning(f"Redis session state set failed: {e}")

	def get_session_state(self, *, session_id: str) -> Optional[SessionState]:
		if not session_id or not redis_tool.ping():
			return None
		key = redis_tool._key("session", session_id)
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return SessionState.model_validate_json(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Redis session state read failed: {e}")
			return None

	# User short-term memory
	def set_user_memory(self, *, user_id: str, memory: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
		if not user_id:
			return
		if not redis_tool.ping():
			return
		key = redis_tool._key("user_memory", user_id)
		try:
			obj = UserShortTermMemory(user_id=user_id, memory=memory)
			exp = int(ttl_seconds or getattr(self._cfg, "user_memory_ttl_seconds", 86400) or 86400)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except Exception as e:
			log_warning(f"Redis user memory set failed: {e}")

	def get_user_memory(self, *, user_id: str) -> Optional[UserShortTermMemory]:
		if not user_id or not redis_tool.ping():
			return None
		key = redis_tool._key("user_memory", user_id)
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return UserShortTermMemory.model_validate_json(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Redis user memory read failed: {e}")
			return None

	# Tool dedup
	def mark_tool_call(self, *, tool_name: str, params: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
		"""Return True if this call is NEW within TTL; False if duplicate."""
		if not redis_tool.ping():
			return True
		exp = int(ttl_seconds or getattr(self._cfg, "tool_dedup_ttl_seconds", 600) or 600)
		key = make_cache_key(prefix=redis_tool._key("tool_dedup", tool_name), parts={"tool": tool_name, "params": params})
		try:
			# SET NX EX
			ok = redis_tool.client().set(key, b"1", nx=True, ex=exp)
			return bool(ok)
		except Exception as e:
			log_warning(f"Redis tool dedup failed: {e}")
			return True

	# Web search cache
	def get_web_cache(self, *, query: str, params: Dict[str, Any]) -> Optional[CachedWebResult]:
		if not redis_tool.ping():
			return None
		key = make_cache_key(prefix=redis_tool._key("web", "cache"), parts={"query": query, "params": params})
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return CachedWebResult.model_validate_json(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Redis web cache read failed: {e}")
			return None

	def set_web_cache(self, *, query: str, params: Dict[str, Any], result: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
		if not redis_tool.ping():
			return
		exp = int(ttl_seconds or getattr(self._cfg, "web_cache_ttl_seconds", 900) or 900)
		key = make_cache_key(prefix=redis_tool._key("web", "cache"), parts={"query": query, "params": params})
		try:
			obj = CachedWebResult(query=query, params=params, result=result)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except Exception as e:
			log_warning(f"Redis web cache set failed: {e}")

	# Retrieval cache
	def get_retrieval_cache(self, *, query: str, k: int) -> Optional[CachedRetrievalResult]:
		if not redis_tool.ping():
			return None
		key = make_cache_key(prefix=redis_tool._key("retrieval", "cache"), parts={"query": query, "k": int(k)})
		try:
			raw = redis_tool.client().get(key)
			if not raw:
				return None
			return CachedRetrievalResult.model_validate_json(raw.decode("utf-8"))
		except Exception as e:
			log_warning(f"Redis retrieval cache read failed: {e}")
			return None

	def set_retrieval_cache(self, *, query: str, k: int, result_text: str, ttl_seconds: Optional[int] = None) -> None:
		if not redis_tool.ping():
			return
		exp = int(ttl_seconds or getattr(self._cfg, "retrieval_cache_ttl_seconds", 1800) or 1800)
		key = make_cache_key(prefix=redis_tool._key("retrieval", "cache"), parts={"query": query, "k": int(k)})
		try:
			obj = CachedRetrievalResult(query=query, k=int(k), result_text=result_text)
			redis_tool.client().set(key, obj.model_dump_json().encode("utf-8"), ex=exp)
		except Exception as e:
			log_warning(f"Redis retrieval cache set failed: {e}")

	# Diagnostics
	def health(self) -> Dict[str, Any]:
		ok = redis_tool.ping()
		cfg = self._cfg
		return {
			"redis_ok": bool(ok),
			"host": cfg.host,
			"port": cfg.port,
			"db": cfg.db,
			"key_prefix": cfg.key_prefix,
			"ts": datetime.utcnow().isoformat(),
		}

	def clear_thread_cache(self, *, thread_id: str) -> Dict[str, bool]:
		"""
		Clear all cached data for a specific thread.
		
		Useful for debugging stale response issues or forcing fresh data.
		
		Args:
			thread_id: The thread ID to clear cache for
		
		Returns:
			Dictionary showing which caches were cleared
		"""
		if not thread_id:
			return {"error": "thread_id required"}
		
		results = {
			"hot_messages": False,
			"warm_summary": False,
			"session_state": False,
			"graph_state": False,
		}
		
		if not redis_tool.ping():
			log_warning("Redis unavailable; cannot clear thread cache")
			return results
		
		client = redis_tool.client()
		
		# Clear hot messages
		try:
			key = redis_tool._key("hot", thread_id)
			results["hot_messages"] = bool(client.delete(key))
		except Exception as e:
			log_warning(f"Failed to clear hot messages: {e}")
		
		# Clear warm summary
		try:
			key = redis_tool._key("warm_summary", thread_id)
			results["warm_summary"] = bool(client.delete(key))
		except Exception as e:
			log_warning(f"Failed to clear warm summary: {e}")
		
		# Clear session state
		try:
			key = redis_tool._key("session", thread_id)
			results["session_state"] = bool(client.delete(key))
		except Exception as e:
			log_warning(f"Failed to clear session state: {e}")
		
		# Clear graph state
		try:
			results["graph_state"] = redis_tool.delete_graph_state(thread_id=thread_id)
		except Exception as e:
			log_warning(f"Failed to clear graph state: {e}")
		
		log_info(f"Cleared thread cache for {thread_id}: {results}")
		return results


cache_service = CacheService()
