"""
Configuration Management for FPT Policy RAG Agent
Centralized configuration for CLI and Web interfaces
"""

import os
from typing import Optional, Literal
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
    """Agent execution configuration"""
    mode: Literal["rag", "web", "hybrid", "chat"] = "rag"
    top_k: int = 5
    model_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than 0")
        
        if self.mode not in {"rag", "web", "hybrid", "chat"}:
            raise ValueError(f"Invalid mode: {self.mode}. Must be one of: rag, web, hybrid, chat")


@dataclass
class VectorDBConfig:
    """Vector database configuration"""
    persist_dir: str = "./app/storage/qdrant"
    collection_name: str = "rag-fpt"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sparse_embedding_model: str = "Qdrant/bm25"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    threshold: float = 0.7
    
    @classmethod
    def from_env(cls) -> "VectorDBConfig":
        """Create configuration from environment variables"""
        return cls(
            persist_dir=os.getenv("QDRANT_PATH", "./app/storage/qdrant"),
            collection_name=os.getenv("QDRANT_COLLECTION", "rag-fpt"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            sparse_embedding_model=os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            threshold=float(os.getenv("THRESHOLD", "0.7"))
        )


@dataclass
class AppConfig:
    """Application-wide configuration"""
    # API Keys
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    
    # Paths
    storage_dir: str = "./app/storage"
    docs_dir: str = "./app/docs"
    
    # Logging
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables"""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            storage_dir=os.getenv("STORAGE_DIR", "./app/storage"),
            docs_dir=os.getenv("DOCS_DIR", "./app/docs"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate paths
        for path_name, path_value in [
            ("storage_dir", self.storage_dir),
            ("docs_dir", self.docs_dir)
        ]:
            path = Path(path_value)
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {path_name} at {path_value}: {e}")
        
        return len(errors) == 0, errors


# Global configuration instances (lazy-loaded)
_app_config: Optional[AppConfig] = None
_vectordb_config: Optional[VectorDBConfig] = None


def get_app_config() -> AppConfig:
    """Get or create application configuration"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.from_env()
    return _app_config


def get_vectordb_config() -> VectorDBConfig:
    """Get or create vector database configuration"""
    global _vectordb_config
    if _vectordb_config is None:
        _vectordb_config = VectorDBConfig.from_env()
    return _vectordb_config
