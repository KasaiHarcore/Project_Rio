"""Reranking service for improving retrieval quality."""

import os
from typing import Optional

from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

from backend.utils.log import log_info, log_warning


class RerankService:
	"""Builds retrievers with optional reranking."""

	def __init__(self, *, vectorstore, score_threshold: Optional[float] = None) -> None:
		self._vectorstore = vectorstore
		self._compressor: Optional[CohereRerank] = None
		self._checked_api_key = False
		self._score_threshold = score_threshold

	def _get_compressor(self) -> Optional[CohereRerank]:
		if self._compressor is not None:
			return self._compressor

		if os.getenv("COHERE_API_KEY"):
			log_info("Initializing Cohere Reranker...")
			self._compressor = CohereRerank(model="rerank-english-v3.0")
			return self._compressor

		if not self._checked_api_key:
			log_warning("COHERE_API_KEY not found. Using standard hybrid search without reranking.")
			self._checked_api_key = True
		return None

	def build_retriever(self, *, k: int = 10):
		base_retriever = None
		if self._score_threshold is not None:
			try:
				base_retriever = self._vectorstore.as_retriever(
					search_type="mmr",
					search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.5, "score_threshold": self._score_threshold},
				)
			except Exception:
				base_retriever = None

		if base_retriever is None:
			base_retriever = self._vectorstore.as_retriever(search_type="similarity", k=k)
		compressor = self._get_compressor()

		if compressor:
			return ContextualCompressionRetriever(
				base_retriever=base_retriever,
				base_compressor=compressor,
			)

		return base_retriever
