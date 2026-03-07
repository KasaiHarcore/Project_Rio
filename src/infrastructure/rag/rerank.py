"""Reranking service for improving retrieval quality."""

import os
from typing import Optional

from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from qdrant_client import models as qdrant_models

from utils.log import log_info, log_warning


def _build_user_filter(user_id: Optional[str]) -> Optional[qdrant_models.Filter]:
	"""Build a Qdrant payload filter scoped to a specific user.

	Returns None when user_id is None (no filtering — admin/system use).
	"""
	if not user_id:
		return None
	return qdrant_models.Filter(
		must=[
			qdrant_models.FieldCondition(
				key="user_id",
				match=qdrant_models.MatchValue(value=user_id),
			)
		]
	)


class RerankService:
	"""Builds retrievers with optional reranking."""

	def __init__(self, *, vectorstore, score_threshold: Optional[float] = None, api_key: Optional[str] = None) -> None:
		self._vectorstore = vectorstore
		self._compressor: Optional[CohereRerank] = None
		self._checked_api_key = False
		self._score_threshold = score_threshold
		self._user_api_key = api_key  # User's Cohere API key (takes precedence over env var)

	def set_user_api_key(self, api_key: Optional[str]) -> None:
		"""Set user's Cohere API key and invalidate cached compressor.

		Args:
			api_key: User's Cohere API key
		"""
		if api_key != self._user_api_key:
			self._user_api_key = api_key
			self._compressor = None  # Invalidate cached compressor
			self._checked_api_key = False

	def _get_compressor(self) -> Optional[CohereRerank]:
		if self._compressor is not None:
			return self._compressor

		# Priority 1: User-specific API key
		api_key = self._user_api_key or os.getenv("COHERE_API_KEY")

		if api_key:
			log_info("Initializing Cohere Reranker..." + (" (user key)" if self._user_api_key else " (env var)"))
			self._compressor = CohereRerank(
				model="rerank-english-v3.0",
				cohere_api_key=api_key,
			)
			return self._compressor

		if not self._checked_api_key:
			log_warning("COHERE_API_KEY not found. Using standard hybrid search without reranking.")
			self._checked_api_key = True
		return None

	def build_retriever(self, *, k: int = 10, user_id: Optional[str] = None):
		qdrant_filter = _build_user_filter(user_id)
		base_retriever = None
		if self._score_threshold is not None:
			try:
				search_kwargs = {
					"k": k, "fetch_k": 20, "lambda_mult": 0.5,
					"score_threshold": self._score_threshold,
				}
				if qdrant_filter:
					search_kwargs["filter"] = qdrant_filter
				base_retriever = self._vectorstore.as_retriever(
					search_type="mmr",
					search_kwargs=search_kwargs,
				)
			except Exception:
				base_retriever = None

		if base_retriever is None:
			search_kwargs = {"k": k}
			if qdrant_filter:
				search_kwargs["filter"] = qdrant_filter
			base_retriever = self._vectorstore.as_retriever(
				search_type="similarity",
				search_kwargs=search_kwargs,
			)
		compressor = self._get_compressor()

		if compressor:
			return ContextualCompressionRetriever(
				base_retriever=base_retriever,
				base_compressor=compressor,
			)

		return base_retriever
