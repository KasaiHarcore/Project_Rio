import os
import atexit
import json
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from pypdf import PdfReader
from langchain_core.vectorstores import VectorStore
from qdrant_client.models import SparseVectorParams, VectorParams, Distance, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import StructuredTool
from langchain_core.documents import Document

from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from chonkie import SemanticChunker
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from qdrant_client import QdrantClient, models


from app.backend.utils.log import log_info, log_success, log_error, log_warning

class VectorDBTool:
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.json', '.csv', '.html', '.htm', '.docx'}
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
        threshold: Optional[float] = None
    ):
        """
        Initialize VectorDBTool with configuration
        """
        # Configuration from environment variables or parameters
        self.persist_dir = persist_dir or os.getenv("QDRANT_PATH", "./app/storage/qdrant")
        self.model_name = embedding_model or os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.sparse_model_name = sparse_embedding_model or os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "rag-fpt")
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", self.DEFAULT_CHUNK_SIZE))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", self.DEFAULT_CHUNK_OVERLAP))
        self.threshold = threshold or float(os.getenv("THRESHOLD", self.THRESHOLD))
        
        self._vectorstore = None
        self._embeddings = None
        self._sparse_embeddings = None
        self._compressor = None
        self._retrieve_rerank = None
        self._client: Optional[QdrantClient] = None
        self._embedding_dim: Optional[int] = None
        
        # Create storage directory
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            log_success(f"Qdrant storage directory ready: {self.persist_dir}")
        except Exception as e:
            log_error(f"Failed to create Qdrant directory: {e}")
            raise
        
        # Initialize everything at once
        self._init_client()
        self._init_embeddings()
        self._ensure_collection()
        self._init_vectorstore()
    
    def _init_client(self):
        """Initialize Qdrant client"""
        if self._client is None:
            log_info("Initializing Qdrant client...")
            try:
                self._client = QdrantClient(path=self.persist_dir)
                atexit.register(self._client.close)
                log_success("Qdrant client initialized")
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
            else:
                log_info(f"Creating new collection: {self.collection_name}")
                embedding_dim = self._get_embedding_dimension()
                
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={"dense": VectorParams(size=embedding_dim, distance=Distance.COSINE)},
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
            collections = self._client.get_collections().collections
            return self.collection_name in [col.name for col in collections]
        except Exception as e:
            log_error(f"Failed to check collection existence: {e}")
            return False
    
    def delete_collection(self) -> bool:
        """Delete the collection (use with caution!)"""
        try:
            if self.collection_exists():
                self._client.delete_collection(self.collection_name)
                log_success(f"Collection '{self.collection_name}' deleted")
                # Reset everything
                self._vectorstore = None
                self._retrieve_rerank = None
                self._compressor = None
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
        self.delete_collection()
        self._ensure_collection()
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
                self._sparse_embeddings = FastEmbedSparse(
                    model_name=self.sparse_model_name
                )
                log_success(f"Embedding model loaded on {device}")
            except Exception as e:
                log_error(f"Failed to load embedding model: {e}")
                raise

    def _init_vectorstore(self):
        """Initialize vector store and reranker"""
        if self._retrieve_rerank is None:
            log_info(f"Connecting to Qdrant collection: {self.collection_name}")
            try:
                self._vectorstore = QdrantVectorStore(
                    client=self._client,
                    collection_name=self.collection_name,
                    embedding=self._embeddings,
                    sparse_embedding=self._sparse_embeddings,
                    retrieval_mode=RetrievalMode.HYBRID,
                    vector_name="dense",
                    sparse_vector_name="sparse"
                )     
                # Check for Cohere API key before initializing reranker
                if os.getenv("COHERE_API_KEY"):
                    log_info("Initializing Cohere Reranker...")
                    self._compressor = CohereRerank(
                        model="rerank-english-v3.0"
                    )
                    self._retrieve_rerank = ContextualCompressionRetriever(
                        base_retriever=self._vectorstore.as_retriever(search_type="similarity", k=10),
                        base_compressor=self._compressor,
                    )
                else:
                    log_warning("COHERE_API_KEY not found. Fallback to standard hybrid search without reranking.")
                    self._retrieve_rerank = self._vectorstore.as_retriever(search_type="similarity", k=10)
                log_success(f"Qdrant vector store ready: {self.collection_name}")
            except Exception as e:
                log_error(f"Failed to initialize vector store: {e}")
                raise

    @property
    def vectorstore(self) -> VectorStore:
        """Get the initialized vector store retriever"""
        return self._retrieve_rerank
    
    def get_chunking_strategy(self, strategy: str = "recursive") -> RecursiveCharacterTextSplitter:
        """
        Get text splitter based on strategy
        
        Args:
            strategy: Chunking strategy ('recursive', 'character', or 'semantic')
            
        Returns:
            Text splitter instance
        """
        if strategy == "character":
            return CharacterTextSplitter(
                separator="\n\n",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
            )
        elif strategy == "recursive":
            return RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=len,
            )
        elif strategy == "semantic":
            return SemanticChunker(
                embedding_model=self.model_name,
                threshold=self.threshold,                               
                chunk_size=self.chunk_size,  
                similarity_window=3,
                skip_window=0
            )
        else:
            log_warning(f"Unknown strategy '{strategy}', using recursive")
            return RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        

    def search_documents(self, query: str, k: int = 10) -> str:
        """
        Search for relevant information within the document knowledge base.
        """
        if not query or not query.strip():
            log_warning("Empty query provided to search_documents")
            return "No query provided."
        
        log_info(f"Searching for: '{query}' (top {k} results)")
        try:
            docs = self._retrieve_rerank.invoke(query)
            log_success(f"Found {len(docs)} relevant document(s)")
            
            if not docs:
                log_warning("No documents found for query")
                return "No relevant documents found in the knowledge base."
            
            parts: list[str] = []
            for idx, d in enumerate(docs, 1):
                source = (d.metadata or {}).get("source", "Unknown")
                page = (d.metadata or {}).get("page")
                chunk = (d.metadata or {}).get("chunk")
                
                header = f"[Result {idx}]"
                if source != "Unknown":
                    header += f" Source: {Path(source).name}"
                if page is not None:
                    header += f" | Page: {page}"
                if chunk is not None:
                    header += f" | Chunk: {chunk}"
                    
                parts.append(f"{header}\n{d.page_content}")
            
            return "\n\n" + "="*60 + "\n\n".join([""] + parts)
        except Exception as e:
            log_error(f"Search failed: {e}")
            return f"Search error: {str(e)}"

    def add_document(
        self, 
        content: str, 
        *, 
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunking_strategy: str = "recursive",
        batch_size: int = None
    ) -> str:
        """
        Add new text content to the knowledge base with batch processing.
        """
        if not content or not content.strip():
            log_warning("Empty content provided to add_document")
            return "No content to index."
        
        batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        log_info(f"Adding document (source: {source or 'inline'}, strategy: {chunking_strategy})")
        
        try:
            splitter = self.get_chunking_strategy(chunking_strategy)
            
            chunks = None
            if chunking_strategy == "semantic":
                chunks = splitter.chunk(content)
            else:
                chunks = splitter.split_text(content)
            
            if not chunks:
                log_warning("No chunks generated from content")
                return "No content chunks generated."
            
            # Prepare metadata
            base_metadata = metadata or {}
            if source:
                base_metadata["source"] = source
            
            metadatas = [
                {**base_metadata, "chunk": i} 
                for i in range(len(chunks))
            ] if base_metadata else None
            
            # Batch processing for large documents
            total_chunks = len(chunks)
            if total_chunks > batch_size:
                log_info(f"Processing {total_chunks} chunks in batches of {batch_size}")
                for i in range(0, total_chunks, batch_size):
                    batch_texts = chunks[i:i + batch_size]
                    batch_metas = metadatas[i:i + batch_size] if metadatas else None
                    self._vectorstore.add_texts(batch_texts, metadatas=batch_metas)
                    log_info(f"Processed batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}")
            else:
                self._vectorstore.add_texts(chunks, metadatas=metadatas)
            
            log_success(f"Indexed {len(chunks)} chunks from {source or 'content'}")
            return f"Successfully indexed {len(chunks)} chunks to the vector store."
        except Exception as e:
            log_error(f"Failed to add document: {e}")
            raise
    
    def ingest_file(self, file_path: str, chunking_strategy: str = "recursive") -> str:
        """
        Ingest a document file into the knowledge base.
        """
        path = Path(file_path)
        
        if not path.exists():
            log_error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            log_error(f"Path is not a file: {file_path}")
            raise FileNotFoundError(f"Path is not a file: {file_path}")

        suffix = path.suffix.lower()
        
        if suffix not in self.SUPPORTED_EXTENSIONS:
            log_error(f"Unsupported file type: {suffix}")
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )
        
        log_info(f"Ingesting {suffix} file: {path.name}")
        
        try:
            # Text files (.txt, .md)
            if suffix in {".txt", ".md"}:
                return self._ingest_text_file(path, chunking_strategy)
            
            # PDF files
            elif suffix == ".pdf":
                return self._ingest_pdf_file(path, chunking_strategy)
            
            # JSON files
            elif suffix == ".json":
                return self._ingest_json_file(path, chunking_strategy)
            
            # CSV files
            elif suffix == ".csv":
                return self._ingest_csv_file(path, chunking_strategy)
            
            # HTML files
            elif suffix in {".html", ".htm"}:
                return self._ingest_html_file(path, chunking_strategy)
            
            # DOCX files
            elif suffix == ".docx":
                return self._ingest_docx_file(path, chunking_strategy)
            
        except Exception as e:
            log_error(f"Failed to ingest {path.name}: {e}")
            raise
    
    def _ingest_text_file(self, path: Path, strategy: str) -> str:
        """Ingest plain text or markdown file"""
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            log_warning(f"File is empty: {path.name}")
            return f"File {path.name} is empty, skipped."
        return self.add_document(
            text, 
            source=str(path),
            metadata={"file_type": path.suffix[1:]},
            chunking_strategy=strategy
        )
    
    def _ingest_pdf_file(self, path: Path, strategy: str) -> str:
        """Ingest PDF file with page-level metadata"""
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)
        log_info(f"Processing PDF with {total_pages} pages")
        
        chunks_data: List[Tuple[str, Dict]] = []
        for i, page in enumerate(reader.pages):
            extracted = page.extract_text() or ""
            if extracted.strip():
                chunks_data.append((
                    extracted, 
                    {
                        "source": str(path), 
                        "page": i + 1,
                        "file_type": "pdf"
                    }
                ))
        
        if not chunks_data:
            log_warning(f"No text extracted from PDF: {path.name}")
            return f"No text content found in {path.name}"
        
        # Split each page and maintain page metadata
        splitter = self.get_chunking_strategy(strategy)
        
        all_texts = []
        all_metadatas = []
        chunk_idx = 0
        
        for page_text, page_meta in chunks_data:
            page_chunks = splitter.split_text(page_text)
            for chunk_text in page_chunks:
                all_texts.append(chunk_text)
                all_metadatas.append({
                    **page_meta,
                    "chunk": chunk_idx
                })
                chunk_idx += 1
        
        # Batch processing
        batch_size = self.DEFAULT_BATCH_SIZE
        if len(all_texts) > batch_size:
            log_info(f"Processing {len(all_texts)} chunks in batches")
            for i in range(0, len(all_texts), batch_size):
                batch_texts = all_texts[i:i + batch_size]
                batch_metas = all_metadatas[i:i + batch_size]
                self._vectorstore.add_texts(batch_texts, metadatas=batch_metas)
        else:
            self._vectorstore.add_texts(all_texts, metadatas=all_metadatas)
        
        log_success(f"Indexed {len(all_texts)} chunks from {total_pages} pages of {path.name}")
        return f"Successfully indexed {len(all_texts)} chunks from {total_pages} page(s) of {path.name}"
    
    def _ingest_json_file(self, path: Path, strategy: str) -> str:
        """Ingest JSON file (converts to text representation)"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert JSON to readable text
        if isinstance(data, dict):
            text = json.dumps(data, indent=2, ensure_ascii=False)
        elif isinstance(data, list):
            # For lists, create separate entries
            text = "\n\n".join([
                json.dumps(item, indent=2, ensure_ascii=False) 
                for item in data
            ])
        else:
            text = str(data)
        
        return self.add_document(
            text,
            source=str(path),
            metadata={"file_type": "json"},
            chunking_strategy=strategy
        )
    
    def _ingest_csv_file(self, path: Path, strategy: str) -> str:
        """Ingest CSV file (converts rows to text)"""
        rows_text = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            for idx, row in enumerate(reader):
                row_text = f"Row {idx + 1}:\n"
                row_text += "\n".join([f"{k}: {v}" for k, v in row.items() if v])
                rows_text.append(row_text)
        
        if not rows_text:
            return f"No data found in {path.name}"
        
        full_text = "\n\n".join(rows_text)
        return self.add_document(
            full_text,
            source=str(path),
            metadata={"file_type": "csv", "headers": str(headers)},
            chunking_strategy=strategy
        )
    
    def _ingest_html_file(self, path: Path, strategy: str) -> str:
        """Ingest HTML file (extracts text)"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            log_error("BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
            raise ImportError("beautifulsoup4 required for HTML parsing")
        
        html_content = path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        
        if not text.strip():
            return f"No text content found in {path.name}"
        
        return self.add_document(
            text,
            source=str(path),
            metadata={"file_type": "html"},
            chunking_strategy=strategy
        )
    
    def _ingest_docx_file(self, path: Path, strategy: str) -> str:
        """Ingest DOCX file"""
        try:
            from docx import Document as DocxDocument
        except ImportError:
            log_error("python-docx not installed. Install with: pip install python-docx")
            raise ImportError("python-docx required for DOCX parsing")
        
        doc = DocxDocument(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        
        if not paragraphs:
            return f"No text content found in {path.name}"
        
        text = "\n\n".join(paragraphs)
        return self.add_document(
            text,
            source=str(path),
            metadata={"file_type": "docx"},
            chunking_strategy=strategy
        )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the current collection
        """
        try:
            if self._client:
                collection_info = self._client.get_collection(self.collection_name)
                
                info = {
                    "collection_name": self.collection_name,
                    "vectors_count": collection_info.points_count if hasattr(collection_info, 'points_count') else 0,
                    "status": "active",
                    "persist_dir": self.persist_dir,
                    "embedding_model": self.model_name,
                    "spare_embedding_model": self.sparse_model_name,
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "threshold": self.threshold
                }
                
                # Add vector config if available
                if hasattr(collection_info, 'config'):
                    config = collection_info.config
                    if hasattr(collection_info.config.params, 'vectors') and "dense" in collection_info.config.params.vectors:
                        info["vector_dimension"] = collection_info.config.params.vectors["dense"].size
                        info["distance_metric"] = collection_info.config.params.vectors["dense"].distance
                    else:
                        info["vector_dimension"] = "Unknown"
                        info["distance_metric"] = "Unknown"
                        
                    if hasattr(collection_info.config.params, 'vectors') and "sparse" in collection_info.config.params.vectors:
                        info["sparse_index"] = collection_info.config.params.vectors["sparse"].index
                    else:
                        info["sparse_index"] = "Unknown"
                        
                return info
        except Exception as e:
            log_warning(f"Could not retrieve collection info: {e}")
        
        return {
            "collection_name": self.collection_name,
            "status": "not initialized",
            "persist_dir": self.persist_dir,
            "embedding_model": self.model_name
        }
    
    def ingest_directory(
        self, 
        dir_path: str, 
        recursive: bool = True,
        file_pattern: Optional[str] = None,
        chunking_strategy: str = "recursive"
    ) -> Dict[str, Any]:
        """
        Ingest all supported files from a directory
        """
        dir_path_obj = Path(dir_path)
        
        if not dir_path_obj.exists() or not dir_path_obj.is_dir():
            raise ValueError(f"Invalid directory: {dir_path}")
        
        log_info(f"Ingesting directory: {dir_path} (recursive={recursive})")
        
        # Find files
        if file_pattern:
            if recursive:
                files = list(dir_path_obj.rglob(file_pattern))
            else:
                files = list(dir_path_obj.glob(file_pattern))
        else:
            # Get all supported files
            files = []
            for ext in self.SUPPORTED_EXTENSIONS:
                pattern = f"**/*{ext}" if recursive else f"*{ext}"
                files.extend(dir_path_obj.glob(pattern))
        
        files = [f for f in files if f.is_file()]
        
        if not files:
            log_warning(f"No files found in {dir_path}")
            return {"total": 0, "success": 0, "failed": 0, "files": []}
        
        log_info(f"Found {len(files)} files to process")
        
        results = {
            "total": len(files),
            "success": 0,
            "failed": 0,
            "files": []
        }
        
        for file_path in files:
            try:
                result = self.ingest_file(str(file_path), chunking_strategy=chunking_strategy)
                results["success"] += 1
                results["files"].append({
                    "path": str(file_path),
                    "status": "success",
                    "message": result
                })
            except Exception as e:
                results["failed"] += 1
                results["files"].append({
                    "path": str(file_path),
                    "status": "failed",
                    "error": str(e)
                })
                log_error(f"Failed to ingest {file_path.name}: {e}")
        
        log_success(f"Directory ingestion complete: {results['success']}/{results['total']} successful")
        return results


vector_db_tool = VectorDBTool()