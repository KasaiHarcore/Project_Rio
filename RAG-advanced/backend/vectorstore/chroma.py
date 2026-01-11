from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


_DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent / "sql"
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(_DEFAULT_PERSIST_DIR))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_basic")
EMBEDDING_MODEL_NAME = os.getenv(
    "CHROMA_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


def _persisted_db_exists(persist_dir: str) -> bool:
    p = Path(persist_dir)
    if not p.exists():
        return False
    # Common Chroma persistence artifacts
    if (p / "chroma.sqlite3").exists():
        return True
    if (p / "index").exists():
        return True
    # Any non-empty directory is a reasonable signal to attempt loading
    try:
        return any(p.iterdir())
    except OSError:
        return False


_splitter: Optional[RecursiveCharacterTextSplitter] = None
_vectordb: Optional[Chroma] = None


def init_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        strip_whitespace=True,
    )


def get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter
    if _splitter is None:
        _splitter = init_splitter()
    return _splitter


def init_vectorstore() -> Chroma:
    # Ensure the persistence directory exists so Chroma can create/open its DB.
    Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)

    # NOTE: An embedding function is required for similarity search (query embedding).
    # This is still loaded, but we do it lazily so importing modules is fast.
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # If data already exists on disk, Chroma will load it from PERSIST_DIR.
    # Creating the Chroma object itself is cheap; the expensive part was eager init.
    _ = _persisted_db_exists(PERSIST_DIR)
    return Chroma(
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


def get_vectordb() -> Chroma:
    global _vectordb
    if _vectordb is None:
        _vectordb = init_vectorstore()
    return _vectordb