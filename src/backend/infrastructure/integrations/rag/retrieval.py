"""Retrieval pipeline for vector search and hybrid rerank retrieval."""

from pathlib import Path
from typing import List, TYPE_CHECKING

from backend.utils.log import log_info, log_success, log_error, log_warning

if TYPE_CHECKING:
	from backend.infrastructure.cache.service import CacheService


def _get_cache_service():
	"""Lazy import to avoid circular dependency."""
	from backend.infrastructure.cache import cache_service
	return cache_service


class RetrievalService:
	"""Handles retrieval and result formatting."""

	def __init__(self, *, vectorstore, rerank_service) -> None:
		self._vectorstore = vectorstore
		self._rerank_service = rerank_service

	def search_documents(self, query: str, k: int = 10) -> str:
		"""Search for relevant information within the document knowledge base."""
		if not query or not query.strip():
			log_warning("Empty query provided to search_documents")
			return "No query provided."

		query_norm = query.strip()
		try:
			cache_service = _get_cache_service()
			cached = cache_service.get_retrieval_cache(query=query_norm, k=int(k))
			if cached and cached.result_text:
				log_info("Returning cached retrieval result")
				return cached.result_text
		except Exception:
			pass

		# Best-effort dedup marker (does not suppress execution; used for observability).
		try:
			cache_svc = _get_cache_service()
			cache_svc.mark_tool_call(tool_name="retrieval", params={"query": query_norm, "k": int(k)})
		except Exception:
			pass

		log_info(f"Searching for: '{query_norm}' (top {k} results)")
		try:
			retriever = self._rerank_service.build_retriever(k=k)
			docs = retriever.invoke(query_norm)
			log_success(f"Found {len(docs)} relevant document(s)")

			if not docs:
				log_warning("No documents found for query")
				return "No relevant documents found in the knowledge base."

			parts: List[str] = []
			for idx, d in enumerate(docs, 1):
				source = (d.metadata or {}).get("source", "Unknown")
				page = (d.metadata or {}).get("page")
				chunk = (d.metadata or {}).get("chunk")

				header = f"### Result {idx}"
				source_name = Path(source).name if source != "Unknown" else "Unknown"
				meta = f"*Source:* {source_name}"
				if page is not None:
					meta += f" | *Page:* {page}"
				if chunk is not None:
					meta += f" | *Chunk:* {chunk}"

				parts.append(f"{header}\n\n{meta}\n\n{d.page_content}")

			result_text = "\n\n---\n\n".join(parts)
			try:
				cache_svc = _get_cache_service()
				cache_svc.set_retrieval_cache(query=query_norm, k=int(k), result_text=result_text)
			except Exception:
				pass
			
			return result_text
		except Exception as e:
			log_error(f"Search failed: {e}")
			return f"Search error: {str(e)}"

