"""Retrieval pipeline for vector search and hybrid rerank retrieval."""

from pathlib import Path
from typing import List

from backend.utils.log import log_info, log_success, log_error, log_warning


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

		log_info(f"Searching for: '{query}' (top {k} results)")
		try:
			retriever = self._rerank_service.build_retriever(k=k)
			docs = retriever.invoke(query)
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

			return "\n\n---\n\n".join(parts)
		except Exception as e:
			log_error(f"Search failed: {e}")
			return f"Search error: {str(e)}"
