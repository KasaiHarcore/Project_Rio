"""Vector Store tool for structured data retrieval and analysis

Manage all lifecycle of Qdrant vector database

VectorDBTool.__init__()  → only create config and prepare storage directory
    │
    └── _ensure_initialized()  → only call initialization once
            ├── _init_client()        → QdrantClient (local path or remote URL)
            ├── _init_embeddings()    → HuggingFace dense + FastEmbed sparse
            ├── _ensure_collection()  → create collection if not exists
            ├── _init_vectorstore()   → LangChain QdrantVectorStore (HYBRID mode)
            └── _init_services()      → delegate for 3 main services:
                    ├── IngestionService  (load document)
                    ├── RetrievalService  (search)
                    └── RerankService     (re-rank)

- Applied Hybrid Retrieval (dense + vector)
- Support .txt, .md, .pdf, .json, .csv, .html/.htm, .docx files or directory ingestion
- Allowed to control information (save, delete) at document level (by metadata)
- Manage collection lifecycle (check existence, delete) with safety checks
"""

import os
import atexit
from typing import Optional, Dict, Any

from qdrant_client.models import SparseVectorParams, VectorParams, Distance
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from qdrant_client import QdrantClient, models


from utils.log import log_info, log_success, log_error, log_warning
from infrastructure.rag.ingestion import IngestionService
from infrastructure.rag.retrieval import RetrievalService
from infrastructure.rag.rerank import RerankService
from core.settings import get_vectordb_config, get_neo4j_config

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
		self._graph_db_tool = None  # GraphDBTool (lazy, opt-in)
		self._initialized = False

		# Storage directory created lazily in _ensure_initialized()

	def startup_check(self) -> Dict[str, Any]:
		"""Full startup initialization (idempotent)."""
		self._ensure_initialized()
		return self.get_collection_info()

	def _ensure_initialized(self) -> None:
		if self._initialized:
			return
		# Create storage directory on first actual use
		try:
			os.makedirs(self.persist_dir, exist_ok=True)
			log_success(f"Qdrant storage directory ready: {self.persist_dir}")
		except Exception as e:
			log_error(f"Failed to create Qdrant directory: {e}")
			raise
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

			# Create payload indexes for multi-tenant filtering (O(log n) lookups)
			for field_name in ("user_id", "document_id"):
				self._client.create_payload_index(
					collection_name=self.collection_name,
					field_name=field_name,
					field_schema=models.PayloadSchemaType.KEYWORD,
				)
			log_success(f"Payload indexes created: user_id, document_id")

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
				# Reset internal state so next operation triggers full re-init
				self._vectorstore = None
				self._rerank_service = None
				self._retrieval_service = None
				self._ingestion_service = None
				self._initialized = False
				return True
			else:
				log_warning(f"Collection '{self.collection_name}' does not exist")
				return False
		except Exception as e:
			log_error(f"Failed to delete collection: {e}")
			raise

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
		"""Initialize ingestion, retrieval, rerank, and (optionally) graph services."""
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

		# Initialize Neo4j graph tool if enabled
		neo4j_config = get_neo4j_config()
		if neo4j_config.enabled:
			try:
				from infrastructure.tools.neo4j_tool import get_graph_db_tool
				self._graph_db_tool = get_graph_db_tool()
				log_info("Neo4j GraphDBTool attached to VectorDBTool")
			except Exception as e:
				log_warning(f"Neo4j init skipped: {e}")
				self._graph_db_tool = None

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

	def search_documents(self, query: str, k: int = 10, *, user_id: Optional[str] = None) -> str:
		"""
		Search for relevant information within the document knowledge base.

		Args:
			query: Search query text.
			k: Number of results to return.
			user_id: If provided, restricts search to this user's documents.
			         Pass None to search all documents (admin / system use).
		"""
		self._ensure_initialized()
		if not self._retrieval_service:
			raise RuntimeError("Retrieval service is not initialized")
		return self._retrieval_service.search_documents(query, k=k, user_id=user_id)

	def ingest_file(
		self,
		file_path: str,
		chunking_strategy: str = "recursive",
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		"""
		Ingest a document file into the knowledge base.
		Also triggers Neo4j entity extraction if enabled.
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		result = self._ingestion_service.ingest_file(
			file_path,
			chunking_strategy=chunking_strategy,
			source_name=source_name,
			metadata=metadata,
		)

		# Trigger Neo4j graph extraction if enabled
		if self._graph_db_tool and self._graph_db_tool.enabled:
			try:
				self._extract_to_graph(file_path, metadata)
			except Exception as e:
				log_warning(f"Graph extraction skipped for {file_path}: {e}")

		return result

	def _extract_to_graph(
		self,
		file_path: str,
		metadata: Optional[Dict[str, Any]] = None,
	) -> None:
		"""Extract entities from a file and store in Neo4j graph."""
		from langchain_core.documents import Document
		from pathlib import Path

		path = Path(file_path)
		try:
			content = path.read_text(encoding="utf-8")
		except UnicodeDecodeError:
			content = path.read_text(encoding="utf-8", errors="ignore")

		if not content.strip():
			return

		# Create LangChain Documents for graph extraction
		# Use the same chunking as vector ingestion for consistency
		splitter = self._ingestion_service.get_chunking_strategy("recursive")
		chunks = splitter.split_text(content)

		base_meta = metadata or {}
		base_meta.setdefault("source", str(path))
		documents = [
			Document(page_content=chunk, metadata={**base_meta, "chunk": i})
			for i, chunk in enumerate(chunks)
		]

		graph_result = self._graph_db_tool.extract_and_store(documents, metadata=base_meta)
		log_info(f"Graph extraction: {graph_result}")

	def ingest_directory(
		self,
		dir_path: str,
		file_pattern: Optional[str] = None,
		recursive: bool = True,
		chunking_strategy: str = "recursive",
		*,
		metadata: Optional[Dict[str, Any]] = None,
	) -> Dict[str, Any]:
		"""Ingest all supported files in a directory.

		Returns dict with keys: total, success, failed, files.
		"""
		self._ensure_initialized()
		if not self._ingestion_service:
			raise RuntimeError("Ingestion service is not initialized")
		return self._ingestion_service.ingest_directory(
			dir_path,
			file_pattern=file_pattern,
			recursive=recursive,
			chunking_strategy=chunking_strategy,
			metadata=metadata,
		)

	def delete_document_vectors(self, document_id: str, *, user_id: Optional[str] = None) -> int:
		"""Delete vectors for a specific document (by payload metadata).

		Returns number of deleted points if available.
		"""
		self._ensure_initialized()
		if not self._client:
			raise RuntimeError("Qdrant client is not initialized")

		conditions = [
			models.FieldCondition(
				key="document_id",
				match=models.MatchValue(value=document_id),
			)
		]
		if user_id:
			conditions.append(
				models.FieldCondition(
					key="user_id",
					match=models.MatchValue(value=user_id),
				)
			)

		payload_filter = models.Filter(must=conditions)

		log_info(f"Deleting vectors for document_id={document_id}")
		result = self._client.delete(
			collection_name=self.collection_name,
			points_selector=payload_filter,
			wait=True,
		)
		deleted = getattr(result, "deleted", None)
		if deleted is None:
			log_success("Vector deletion request submitted")
			deleted = 0
		else:
			deleted = int(deleted)
			log_success(f"Deleted {deleted} vectors for document_id={document_id}")

		# Also clean up Neo4j graph data if enabled
		if self._graph_db_tool and self._graph_db_tool.enabled:
			try:
				graph_deleted = self._graph_db_tool.delete_document_graph(document_id)
				log_info(f"Deleted {graph_deleted} graph nodes for document_id={document_id}")
			except Exception as e:
				log_warning(f"Graph cleanup failed for document_id={document_id}: {e}")

		return deleted


_vector_db_tool_instance: Optional[VectorDBTool] = None


def get_vector_db_tool() -> VectorDBTool:
	"""Lazy singleton getter — nothing runs until first call."""
	global _vector_db_tool_instance
	if _vector_db_tool_instance is None:
		_vector_db_tool_instance = VectorDBTool()
	return _vector_db_tool_instance
