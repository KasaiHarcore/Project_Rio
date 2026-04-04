"""Note Vector Store — Qdrant collection dedicated to note embeddings.

Provides:
- Upsert note embeddings on create/update
- Delete note embeddings on delete
- Semantic search across user's notes
- Separate collection from document embeddings

Uses the same embedding models as VectorDBTool but with a dedicated
'note_embeddings' Qdrant collection.
"""

import os
from typing import Optional, List, Dict, Any

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    VectorParams, Distance,
    PointStruct, Filter, FieldCondition, MatchValue,
)
from langchain_huggingface import HuggingFaceEmbeddings

from core.settings import get_vectordb_config
from utils.log import log_info, log_success, log_error, log_warning


COLLECTION_NAME = "note_embeddings"


class NoteVectorTool:
    """Qdrant vector store for note semantic search.

    Manages a dedicated 'note_embeddings' collection, separate from
    the document embeddings used by VectorDBTool.
    """

    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
        self._embedding_dim: Optional[int] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._init_client()
        self._init_embeddings()
        self._ensure_collection()
        self._initialized = True

    def _init_client(self) -> None:
        if self._client is not None:
            return

        # Reuse the Qdrant client from VectorDBTool to avoid local storage
        # lock conflicts. Local Qdrant only allows one client per storage dir.
        try:
            from infrastructure.data_access.qdrant_tool import get_vector_db_tool
            vdb = get_vector_db_tool()
            vdb._ensure_initialized()
            if vdb._client is not None:
                self._client = vdb._client
                log_info("NoteVectorTool: reusing shared Qdrant client from VectorDBTool")
                return
        except Exception:
            pass  # Fall through to standalone init

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
                config = get_vectordb_config()
                persist_dir = os.getenv("QDRANT_PATH", config.persist_dir)
                os.makedirs(persist_dir, exist_ok=True)
                self._client = QdrantClient(path=persist_dir)
        except Exception as e:
            log_error(f"NoteVectorTool: Failed to init Qdrant client: {e}")
            raise

    def _init_embeddings(self) -> None:
        if self._embeddings is not None:
            return

        # Try to reuse the embedding model from the primary VectorDBTool
        # to avoid loading the same HuggingFace model twice (~500MB)
        try:
            from infrastructure.data_access.qdrant_tool import get_vector_db_tool
            vdb = get_vector_db_tool()
            if vdb._embeddings is not None and vdb._embedding_dim:
                self._embeddings = vdb._embeddings
                self._embedding_dim = vdb._embedding_dim
                log_info(f"NoteVectorTool: reusing shared embeddings (dim={self._embedding_dim})")
                return
        except Exception:
            pass  # Fall through to standalone init

        config = get_vectordb_config()
        model_name = os.getenv("EMBEDDING_MODEL", config.embedding_model)
        device = os.getenv("EMBEDDING_DEVICE")
        if not device:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
        self._embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
        )
        override_dim = os.getenv("EMBEDDING_DIM")
        if override_dim and override_dim.strip():
            self._embedding_dim = int(override_dim)
        else:
            test = self._embeddings.embed_query("test")
            self._embedding_dim = len(test)
        log_info(f"NoteVectorTool: embeddings ready (dim={self._embedding_dim})")

    def _ensure_collection(self) -> None:
        try:
            collections = self._client.get_collections().collections
            names = [c.name for c in collections]
            if COLLECTION_NAME in names:
                log_info(f"NoteVectorTool: collection '{COLLECTION_NAME}' exists")
                return

            log_info(f"NoteVectorTool: creating collection '{COLLECTION_NAME}'")
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": VectorParams(size=self._embedding_dim, distance=Distance.COSINE)
                },
            )
            for field in ("user_id", "note_id", "collection_ids"):
                self._client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            log_success(f"NoteVectorTool: collection '{COLLECTION_NAME}' created")
        except Exception as e:
            log_error(f"NoteVectorTool: failed to ensure collection: {e}")
            raise

    def upsert_note(
        self,
        note_id: str,
        user_id: str,
        title: str,
        content: str,
        collection_ids: Optional[List[str]] = None,
        source: str = "user",
    ) -> None:
        """Embed and upsert a note into Qdrant.

        Called on note create and update. Combines title + content for embedding.
        """
        self._ensure_initialized()
        text = f"{title}\n\n{content}" if title else content
        if not text.strip():
            return

        try:
            vector = self._embeddings.embed_query(text)
            point = PointStruct(
                id=note_id.replace("-", ""),
                vector={"dense": vector},
                payload={
                    "user_id": user_id,
                    "note_id": note_id,
                    "title": title or "",
                    "source": source,
                    "collection_ids": collection_ids or [],
                    "content_preview": content[:500] if content else "",
                },
            )
            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=[point],
                wait=False,
            )
        except Exception as e:
            log_warning(f"NoteVectorTool: upsert failed for note {note_id}: {e}")

    def delete_note(self, note_id: str) -> None:
        """Remove a note's embedding from Qdrant."""
        self._ensure_initialized()
        try:
            self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="note_id",
                            match=MatchValue(value=note_id),
                        )
                    ]
                ),
                wait=False,
            )
        except Exception as e:
            log_warning(f"NoteVectorTool: delete failed for note {note_id}: {e}")

    def search(
        self,
        query: str,
        user_id: str,
        collection_id: Optional[str] = None,
        k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Semantic search across a user's notes.

        Returns list of dicts with keys: note_id, title, content_preview, score
        """
        self._ensure_initialized()
        if not query.strip():
            return []

        try:
            vector = self._embeddings.embed_query(query)
            conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
            if collection_id:
                conditions.append(
                    FieldCondition(key="collection_ids", match=MatchValue(value=collection_id))
                )

            results = self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                using="dense",
                query_filter=Filter(must=conditions),
                limit=k,
                with_payload=True,
            )

            hits = []
            for point in results.points:
                payload = point.payload or {}
                hits.append({
                    "note_id": payload.get("note_id", ""),
                    "title": payload.get("title", ""),
                    "content_preview": payload.get("content_preview", ""),
                    "score": point.score,
                    "source": payload.get("source", ""),
                })
            return hits
        except Exception as e:
            log_warning(f"NoteVectorTool: search failed: {e}")
            return []


_instance: Optional[NoteVectorTool] = None


def get_note_vector_tool() -> NoteVectorTool:
    """Lazy singleton getter."""
    global _instance
    if _instance is None:
        _instance = NoteVectorTool()
    return _instance
