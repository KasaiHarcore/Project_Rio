"""Vector Store tool for structured data retrieval and analysis"""

import os
import atexit
from typing import Optional, Dict, Any, Tuple

from langchain_core.vectorstores import VectorStore
from qdrant_client.models import SparseVectorParams, VectorParams, Distance
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from qdrant_client import QdrantClient, models


from backend.utils.log import log_info, log_success, log_error, log_warning
from backend.services.rag.ingestion_service import IngestionService
from backend.services.rag.retrieval_service import RetrievalService
from backend.services.rag.rerank_service import RerankService
from backend.core.settings import get_vectordb_config

class VectorDBTool:
	SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".html", ".htm", ".docx"}
	DEFAULT_CHUNK_SIZE = 1000
	DEFAULT_CHUNK_OVERLAP = 200
	DEFAULT_BATCH_SIZE = 100
	THRESHOLD = 0.7

	def __init__(
		self,
		persist_dir: Optional[str] = None,
		collection_name: Optional[str] = None,
		embedding_model: Optional[str] = None,
		sparse_embedding_model: Optional[str] = None,
		chunk_size: Optional[int] = None,
		chunk_overlap: Optional[int] = None,
		threshold: Optional[float] = None,
		retrieval_score_threshold: Optional[float] = None,
		autocreate: Optional[bool] = None,
		eager_init: Optional[bool] = None,
	):
		"""
		Initialize VectorDBTool with configuration
		"""
		# Configuration from environment variables or parameters
		config = get_vectordb_config()
		self.persist_dir = persist_dir or os.getenv("QDRANT_PATH", config.persist_dir)
		self.model_name = embedding_model or os.getenv(
			"EMBEDDING_MODEL", config.embedding_model
		)
		self.sparse_model_name = sparse_embedding_model or os.getenv(
			"SPARSE_EMBEDDING_MODEL", config.sparse_embedding_model
		)
		self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", config.collection_name)
		self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", str(config.chunk_size)))
		self.chunk_overlap = chunk_overlap or int(
			os.getenv("CHUNK_OVERLAP", str(config.chunk_overlap))
		)
		self.threshold = threshold or float(os.getenv("THRESHOLD", str(config.threshold)))
		self.retrieval_score_threshold = (
			retrieval_score_threshold
			if retrieval_score_threshold is not None
			else config.retrieval_score_threshold
		)
		self.autocreate = (
			autocreate
			if autocreate is not None
			else config.vector_db_autocreate
		)
		self.eager_init = (
			eager_init
			if eager_init is not None
			else config.vector_db_eager_init
		)

		self._vectorstore = None
		self._embeddings = None
		self._sparse_embeddings = None
		self._client: Optional[QdrantClient] = None
		self._embedding_dim: Optional[int] = None
		self._ingestion_service: Optional[IngestionService] = None
		self._retrieval_service: Optional[RetrievalService] = None
		self._rerank_service: Optional[RerankService] = None
		self._initialized = False

		# Create storage directory
		try:
			os.makedirs(self.persist_dir, exist_ok=True)
			log_success(f"Qdrant storage directory ready: {self.persist_dir}")
		except Exception as e:
			log_error(f"Failed to create Qdrant directory: {e}")
			raise

	def startup_check(self) -> Dict[str, Any]:
		"""Full startup initialization (idempotent)."""
		self._ensure_initialized()
		return self.get_collection_info()

	def _ensure_initialized(self) -> None:
		if self._initialized:
			return
		self._init_client()
		self._init_embeddings()
		self._ensure_collection()
		self._init_vectorstore()
		self._init_services()
		self._initialized = True

	def _init_client(self):
		"""Initialize Qdrant client"""
		if self._client is None:
			log_info("Initializing Qdrant client...")
			try:
				qdrant_url = os.getenv("QDRANT_URL")
				qdrant_api_key = os.getenv("QDRANT_API_KEY")
				if qdrant_url:
					self._client = QdrantClient(
						url=qdrant_url,
						api_key=qdrant_api_key,
						prefer_grpc=os.getenv("QDRANT_PREFER_GRPC", "False").lower() == "true",
					)
				else:
					self._client = QdrantClient(path=self.persist_dir)
				atexit.register(self._client.close)
			except Exception as e:
				log_error(f"Failed to initialize Qdrant client: {e}")
				raise

	def _get_embedding_dimension(self) -> int:
		"""Get embedding dimension from model"""
		if self._embedding_dim is None:
			if self._embeddings is None:
				self._init_embeddings()
			# Get dimension by embedding a test string
			try:
				override_dim = os.getenv("EMBEDDING_DIM")
				if override_dim and override_dim.strip():
					self._embedding_dim = int(override_dim)
				else:
					test_embedding = self._embeddings.embed_query("test")
					self._embedding_dim = len(test_embedding)
				log_info(f"Embedding dimension: {self._embedding_dim}")
			except Exception as e:
				log_error(f"Failed to get embedding dimension: {e}")
				raise
		return self._embedding_dim

	def _ensure_collection(self):
		"""
		Ensure collection exists, create if necessary

		Checks if collection exists and creates it with proper configuration if not.
		"""
		try:
			collections = self._client.get_collections().collections
			collection_names = [col.name for col in collections]

			if self.collection_name in collection_names:
				log_info(f"Collection '{self.collection_name}' already exists")
				# Verify collection is healthy
				collection_info = self._client.get_collection(self.collection_name)
				log_success(f"Collection verified: {collection_info.points_count} vectors")
				return

			if not self.autocreate:
				raise RuntimeError(
					f"Collection '{self.collection_name}' does not exist and autocreate is disabled."
				)

			log_info(f"Creating new collection: {self.collection_name}")
			embedding_dim = self._get_embedding_dimension()

			self._client.create_collection(
				collection_name=self.collection_name,
				vectors_config={
					"dense": VectorParams(size=embedding_dim, distance=Distance.COSINE)
				},
				sparse_vectors_config={
					"sparse": SparseVectorParams(index=models.SparseIndexParams(on_disk=False))
				},
			)
			log_success(f"Collection '{self.collection_name}' created successfully")
		except Exception as e:
			log_error(f"Failed to ensure collection: {e}")
			raise

	def collection_exists(self) -> bool:
		"""Check if collection exists"""
		try:
			self._ensure_initialized()
			collections = self._client.get_collections().collections
			return self.collection_name in [col.name for col in collections]
		except Exception as e:
			log_error(f"Failed to check collection existence: {e}")
			return False

	def delete_collection(self) -> bool:
		"""Delete the collection (use with caution!)"""
		try:
			self._ensure_initialized()
			if self.collection_exists():
				self._client.delete_collection(self.collection_name)
				log_success(f"Collection '{self.collection_name}' deleted")
				# Reset everything
				self._vectorstore = None
				self._rerank_service = None
				self._retrieval_service = None
				self._ingestion_service = None
				return True
			else:
				log_warning(f"Collection '{self.collection_name}' does not exist")
				return False
		except Exception as e:
			log_error(f"Failed to delete collection: {e}")
			raise

	def recreate_collection(self):
		"""Delete and recreate collection"""
		log_info(f"Recreating collection '{self.collection_name}'")
		self._ensure_initialized()
		self.delete_collection()
		self._ensure_collection()
		self._init_vectorstore()
		self._init_services()
		log_success("Collection recreated successfully")

	def _init_embeddings(self):
		"""Initialize embedding model"""
		if self._embeddings is None:
			device = os.getenv("EMBEDDING_DEVICE")
			if not device:
				try:
					import torch

					device = "cuda" if torch.cuda.is_available() else "cpu"
				except Exception:
					device = "cpu"

			log_info(f"Loading embedding model: {self.model_name} on {device}")
			try:
				self._embeddings = HuggingFaceEmbeddings(
					model_name=self.model_name,
					model_kwargs={"device": device},
				)
				self._sparse_embeddings = FastEmbedSparse(model_name=self.sparse_model_name)
				log_success(f"Embedding model loaded on {device}")
			except Exception as e:
				log_error(f"Failed to load embedding model: {e}")
				raise

	def _init_vectorstore(self):
		"""Initialize vector store and reranker"""
		if self._vectorstore is None:
			log_info(f"Connecting to Qdrant collection: {self.collection_name}")
			try:
				self._vectorstore = QdrantVectorStore(
					client=self._client,
					collection_name=self.collection_name,
					embedding=self._embeddings,
					sparse_embedding=self._sparse_embeddings,
					retrieval_mode=RetrievalMode.HYBRID,
					vector_name="dense",
					sparse_vector_name="sparse",
				)
				log_success(f"Qdrant vector store ready: {self.collection_name}")
			except Exception as e:
				log_error(f"Failed to initialize vector store: {e}")
				raise

	def _init_services(self) -> None:
		"""Initialize ingestion, retrieval, and rerank services."""
		self._rerank_service = RerankService(
			vectorstore=self._vectorstore,
			score_threshold=self.retrieval_score_threshold,
		)
		self._retrieval_service = RetrievalService(
			vectorstore=self._vectorstore,
			rerank_service=self._rerank_service,
		)
		self._ingestion_service = IngestionService(
			vectorstore=self._vectorstore,
			model_name=self.model_name,
			chunk_size=self.chunk_size,
			chunk_overlap=self.chunk_overlap,
			threshold=self.threshold,
			supported_extensions=self.SUPPORTED_EXTENSIONS,
			default_batch_size=self.DEFAULT_BATCH_SIZE,
		)

	@property
	def vectorstore(self) -> VectorStore:
		"""Get the initialized vector store"""
		self._ensure_initialized()
		return self._vectorstore

	def get_collection_info(self) -> Dict[str, Any]:
		"""Return collection metadata for status and diagnostics."""
		try:
			self._ensure_initialized()
			collection_info = self._client.get_collection(self.collection_name)

			vector_params = None
			try:
				vectors_config = collection_info.config.params.vectors
				if isinstance(vectors_config, dict):
					vector_params = vectors_config.get("dense") or next(iter(vectors_config.values()))
				else:
					vector_params = vectors_config
			except Exception:
				vector_params = None

			result: Dict[str, Any] = {
				"collection_name": self.collection_name,
				"status": getattr(collection_info, "status", None),
				"vectors_count": getattr(collection_info, "points_count", None),
				"persist_dir": self.persist_dir,
				"embedding_model": self.model_name,
				"chunk_size": self.chunk_size,
				"chunk_overlap": self.chunk_overlap,
			}

			if vector_params is not None:
				result["vector_dimension"] = getattr(vector_params, "size", None)
				distance = getattr(vector_params, "distance", None)
				result["distance_metric"] = getattr(distance, "value", distance)

			return result
		except Exception as e:
			log_error(f"Failed to retrieve collection info: {e}")
			raise

	def get_chunking_strategy(self, strategy: str = "recursive"):
		"""
		Get text splitter based on strategy
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		return self._ingestion_service.get_chunking_strategy(strategy)

	def search_documents(self, query: str, k: int = 10) -> str:
		"""
		Search for relevant information within the document knowledge base.
		"""
		self._ensure_initialized()
		if not self._retrieval_service:
			raise RuntimeError("Retrieval service is not initialized")
		return self._retrieval_service.search_documents(query, k=k)

	def add_document(
		self,
		content: str,
		*,
		source: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
		chunking_strategy: str = "recursive",
		batch_size: int = None,
	) -> str:
		"""
		Add new text content to the knowledge base with batch processing.
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		return self._ingestion_service.add_document(
			content,
			source=source,
			metadata=metadata,
			chunking_strategy=chunking_strategy,
			batch_size=batch_size,
		)

	def ingest_file(self, file_path: str, chunking_strategy: str = "recursive") -> str:
		"""
		Ingest a document file into the knowledge base.
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		return self._ingestion_service.ingest_file(file_path, chunking_strategy=chunking_strategy)

	def ingest_directory(
		self,
		dir_path: str,
		file_pattern: Optional[str] = None,
		recursive: bool = True,
		chunking_strategy: str = "recursive",
	) -> Dict[str, Any]:
		"""
		Ingest all supported files in a directory
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		return self._ingestion_service.ingest_directory(
			dir_path,
			file_pattern=file_pattern,
			recursive=recursive,
			chunking_strategy=chunking_strategy,
		)

	def get_retriever_tool(self, *, default_k: int = 5) -> "StructuredTool":
		"""Get LangChain StructuredTool for vector retrieval."""
		from langchain_core.tools import StructuredTool
		from pydantic import BaseModel, Field

		class VectorSearchInput(BaseModel):
			query: str = Field(..., description="Search query for policy documents")
			k: int = Field(default=default_k, description="Number of results to retrieve")

		def _run_retriever(query: str, k: int = default_k) -> str:
			return self.search_documents(query, k=k)

		return StructuredTool.from_function(
			name="regular_retriever",
			description=(
				"Standard hybrid search (dense vector + sparse keyword) in database. "
				"Use for straightforward queries with clear keywords. "
			),
			func=_run_retriever,
			args_schema=VectorSearchInput,
		)


vector_db_tool = VectorDBTool()
