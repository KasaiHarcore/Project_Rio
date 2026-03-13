"""Ingestion pipeline for files and metadata."""

import csv
import json
import io
import os
from pathlib import Path
from typing import Optional, Dict, Any, Set, Iterable, List

import requests
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from chonkie import SemanticChunker

from utils.log import log_info, log_success, log_error, log_warning


class MarkdownFormatter:
	"""Utility for normalizing extracted content into Markdown."""

	@classmethod
	def normalize_text(cls, text: str) -> str:
		cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
		# Collapse excessive blank lines to at most two
		lines = [line.rstrip() for line in cleaned.split("\n")]
		result: List[str] = []
		blank_count = 0
		for line in lines:
			if line.strip() == "":
				blank_count += 1
				if blank_count <= 2:
					result.append("")
			else:
				blank_count = 0
				result.append(line)
		return "\n".join(result).strip()

	@classmethod
	def wrap_pages(cls, pages: Iterable[tuple[int, str]], *, source_name: str) -> str:
		parts = [f"# {source_name}", ""]
		for page_num, page_text in pages:
			parts.append(f"## Page {page_num}")
			parts.append("")
			parts.append(MarkdownFormatter.normalize_text(page_text))
			parts.append("")
		return "\n".join(parts).strip()

	@classmethod
	def json_to_markdown(cls, data: Any) -> str:
		payload = json.dumps(data, ensure_ascii=False, indent=2)
		return f"```json\n{payload}\n```"

	@classmethod
	def csv_to_markdown(cls, rows: List[List[str]]) -> str:
		if not rows:
			return ""
		col_count = max(len(r) for r in rows)
		normalized = [r + [""] * (col_count - len(r)) for r in rows]
		headers = normalized[0]
		separator = ["---"] * col_count
		body = normalized[1:]

		def row_to_md(row: List[str]) -> str:
			return "| " + " | ".join(cell.strip() for cell in row) + " |"

		parts = [row_to_md(headers), row_to_md(separator)]
		parts.extend(row_to_md(r) for r in body)
		return "\n".join(parts)

	@classmethod
	def html_to_markdown(cls, raw_html: str) -> str:
		return f"```html\n{raw_html.strip()}\n```"

	@classmethod
	def plain_to_markdown(cls, text: str) -> str:
		return MarkdownFormatter.normalize_text(text)

	@classmethod
	def docx_to_markdown(cls, paragraphs: List[str]) -> str:
		return "\n\n".join(MarkdownFormatter.normalize_text(p) for p in paragraphs if p.strip())


class ExternalOCRClient:
	"""External OCR client to process scanned PDFs without local OCR."""

	def __init__(self) -> None:
		self.api_url = os.getenv("OCR_API_URL", "").strip()
		self.api_key = os.getenv("OCR_API_KEY", "").strip()
		self.api_key_header = os.getenv("OCR_API_KEY_HEADER", "Authorization").strip() or "Authorization"
		self.api_key_prefix = os.getenv("OCR_API_KEY_PREFIX", "Bearer ")
		self.timeout_seconds = int(os.getenv("OCR_TIMEOUT", "120"))
		self.max_file_mb = float(os.getenv("OCR_MAX_FILE_MB", "15"))

	def is_configured(self) -> bool:
		return bool(self.api_url)

	def extract_markdown_from_pdf(self, path: Path) -> str:
		if not self.is_configured():
			log_warning("OCR_API_URL is not configured. Skipping OCR for scanned PDF.")
			return ""

		try:
			size_mb = path.stat().st_size / (1024 * 1024)
			if size_mb > self.max_file_mb:
				log_warning(
					f"OCR skipped for {path.name}: file size {size_mb:.2f}MB exceeds {self.max_file_mb:.2f}MB limit"
				)
				return ""
		except Exception as e:
			log_warning(f"OCR size check failed for {path.name}: {e}")
			return ""

		headers = {}
		if self.api_key:
			headers[self.api_key_header] = f"{self.api_key_prefix}{self.api_key}".strip()

		with open(path, "rb") as f:
			files = {"file": (path.name, f, "application/pdf")}
			data = {"response_format": "markdown"}
			response = requests.post(
				self.api_url,
				headers=headers,
				files=files,
				data=data,
				timeout=self.timeout_seconds,
			)
			response.raise_for_status()

		payload = response.json() if response.content else {}
		markdown = payload.get("markdown") or payload.get("text") or ""
		return MarkdownFormatter.normalize_text(markdown)


class IngestionService:
	"""Handles file ingestion and chunking for the vector store."""

	def __init__(
		self,
		*,
		vectorstore,
		model_name: str,
		chunk_size: int,
		chunk_overlap: int,
		threshold: float,
		supported_extensions: Set[str],
		default_batch_size: int,
	) -> None:
		self._vectorstore = vectorstore
		self.model_name = model_name
		self.chunk_size = chunk_size
		self.chunk_overlap = chunk_overlap
		self.threshold = threshold
		self.supported_extensions = supported_extensions
		self.default_batch_size = default_batch_size
		self._ocr_client = ExternalOCRClient()
		self.max_file_mb = float(os.getenv("MAX_INGEST_FILE_MB", "25"))

	def get_chunking_strategy(self, strategy: str = "recursive"):
		"""Get text splitter based on strategy."""
		if strategy == "character":
			return CharacterTextSplitter(
				separator="\n\n",
				chunk_size=self.chunk_size,
				chunk_overlap=self.chunk_overlap,
				length_function=len,
			)
		if strategy == "recursive":
			return RecursiveCharacterTextSplitter(
				chunk_size=self.chunk_size,
				chunk_overlap=self.chunk_overlap,
				separators=["\n\n", "\n", ". ", " ", ""],
				length_function=len,
			)
		if strategy == "semantic":
			return SemanticChunker(
				embedding_model=self.model_name,
				threshold=self.threshold,
				chunk_size=self.chunk_size,
				similarity_window=3,
				skip_window=0,
			)

		log_warning(f"Unknown strategy '{strategy}', using recursive")
		return RecursiveCharacterTextSplitter(
			chunk_size=self.chunk_size,
			chunk_overlap=self.chunk_overlap,
		)

	def add_document(
		self,
		content: str,
		*,
		source: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
		chunking_strategy: str = "recursive",
		batch_size: Optional[int] = None,
	) -> str:
		"""Add new text content to the knowledge base with batch processing."""
		if not content or not content.strip():
			log_warning("Empty content provided to add_document")
			return "No content to index."

		batch_size = batch_size or self.default_batch_size
		log_info(f"Adding document (source: {source or 'inline'}, strategy: {chunking_strategy})")

		try:
			splitter = self.get_chunking_strategy(chunking_strategy)

			chunks = splitter.chunk(content) if chunking_strategy == "semantic" else splitter.split_text(content)

			if not chunks:
				log_warning("No chunks generated from content")
				return "No content chunks generated."

			base_metadata = metadata or {}
			if source:
				path = Path(source)
				base_metadata.setdefault("source", source)
				base_metadata.setdefault("source_name", path.name)
				base_metadata.setdefault("file_ext", path.suffix.lower())
				base_metadata.setdefault("doc_type", path.suffix.lower().lstrip("."))

			metadatas = (
				[{**base_metadata, "chunk": i} for i in range(len(chunks))]
				if base_metadata
				else None
			)

			total_chunks = len(chunks)
			if total_chunks > batch_size:
				log_info(f"Processing {total_chunks} chunks in batches of {batch_size}")
				for i in range(0, total_chunks, batch_size):
					batch_texts = chunks[i : i + batch_size]
					batch_metas = metadatas[i : i + batch_size] if metadatas else None
					self._vectorstore.add_texts(batch_texts, metadatas=batch_metas)
					log_info(
						f"Processed batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}"
					)
			else:
				self._vectorstore.add_texts(chunks, metadatas=metadatas)

			log_success(f"Indexed {len(chunks)} chunks from {source or 'content'}")
			return f"Successfully indexed {len(chunks)} chunks to the vector store."
		except Exception as e:
			log_error(f"Failed to add document: {e}")
			raise

	def ingest_file(
		self,
		file_path: str,
		chunking_strategy: str = "recursive",
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		"""Ingest a document file into the knowledge base."""
		path = Path(file_path)

		if not path.exists():
			log_error(f"File not found: {file_path}")
			raise FileNotFoundError(f"File not found: {file_path}")

		if not path.is_file():
			log_error(f"Path is not a file: {file_path}")
			raise FileNotFoundError(f"Path is not a file: {file_path}")

		self._validate_file_size(path)

		suffix = path.suffix.lower()

		if suffix not in self.supported_extensions:
			log_error(f"Unsupported file type: {suffix}")
			raise ValueError(
				f"Unsupported file type: {suffix}. "
				f"Supported: {', '.join(sorted(self.supported_extensions))}"
			)

		log_info(f"Ingesting {suffix} file: {path.name}")

		try:
			if suffix in {".txt", ".md"}:
				return self._ingest_text_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			elif suffix == ".pdf":
				return self._ingest_pdf_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			elif suffix == ".json":
				return self._ingest_json_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			elif suffix == ".csv":
				return self._ingest_csv_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			elif suffix in {".html", ".htm"}:
				return self._ingest_html_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			elif suffix == ".docx":
				return self._ingest_docx_file(
					path,
					chunking_strategy,
					source_name=source_name,
					metadata=metadata,
				)
			else:
				raise ValueError(f"Unsupported file type: {suffix}")

		except Exception as e:
			log_error(f"Failed to ingest file {path.name}: {e}")
			raise

	def ingest_directory(
		self,
		dir_path: str,
		file_pattern: Optional[str] = None,
		recursive: bool = True,
		chunking_strategy: str = "recursive",
		*,
		metadata: Optional[Dict[str, Any]] = None,
	) -> Dict[str, Any]:
		"""Ingest all supported files in a directory."""
		dir_path_obj = Path(dir_path)

		if not dir_path_obj.exists():
			log_error(f"Directory not found: {dir_path}")
			raise FileNotFoundError(f"Directory not found: {dir_path}")

		if not dir_path_obj.is_dir():
			log_error(f"Path is not a directory: {dir_path}")
			raise NotADirectoryError(f"Path is not a directory: {dir_path}")

		if file_pattern:
			files = list(dir_path_obj.rglob(file_pattern)) if recursive else list(dir_path_obj.glob(file_pattern))
		else:
			files = []
			for ext in self.supported_extensions:
				pattern = f"**/*{ext}" if recursive else f"*{ext}"
				files.extend(dir_path_obj.glob(pattern))

		files = [f for f in files if f.is_file()]

		if not files:
			log_warning(f"No files found in {dir_path}")
			return {"total": 0, "success": 0, "failed": 0, "files": []}

		log_info(f"Found {len(files)} files to process")

		results = {"total": len(files), "success": 0, "failed": 0, "files": []}

		for file_path in files:
			try:
				result = self.ingest_file(
					str(file_path),
					chunking_strategy=chunking_strategy,
					metadata=metadata,
				)
				results["success"] += 1
				results["files"].append(
					{"path": str(file_path), "status": "success", "message": result}
				)
			except Exception as e:
				results["failed"] += 1
				results["files"].append(
					{"path": str(file_path), "status": "failed", "error": str(e)}
				)
				log_error(f"Failed to ingest {file_path.name}: {e}")

		log_success(
			f"Directory ingestion complete: {results['success']}/{results['total']} successful"
		)
		return results

	def _ingest_text_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			content = self._read_text_utf8(path)
			if not content.strip():
				raise ValueError("Text file is empty")
			markdown = MarkdownFormatter.plain_to_markdown(content)
			return self.add_document(
				markdown,
				source=source_name or str(path),
				metadata=metadata,
				chunking_strategy=chunking_strategy,
			)
		except Exception as e:
			log_error(f"Failed to read text file: {e}")
			raise

	def _ingest_pdf_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			reader = PdfReader(str(path))
			pages: List[tuple[int, str]] = []
			metadatas = []
			base_meta = metadata or {}

			for page_num, page in enumerate(reader.pages, 1):
				text = page.extract_text()
				if text and text.strip():
					pages.append((page_num, text))
					metadatas.append({
						**base_meta,
						"source": source_name or str(path),
						"source_name": source_name or path.name,
						"file_ext": path.suffix.lower(),
						"doc_type": "pdf",
						"page": page_num,
					})

			if not pages:
				log_warning(f"No text extracted from PDF: {path.name}. Attempting OCR...")
				ocr_markdown = self._ocr_client.extract_markdown_from_pdf(path)
				if not ocr_markdown:
					log_warning(f"OCR produced no text for PDF: {path.name}")
					return "No text extracted from PDF."
				return self.add_document(
					ocr_markdown,
					source=source_name or str(path),
					metadata=metadata,
					chunking_strategy=chunking_strategy,
				)

			total_chunks = 0
			splitter = self.get_chunking_strategy(chunking_strategy)

			for (page_num, text), metadata in zip(pages, metadatas):
				page_markdown = MarkdownFormatter.wrap_pages([(page_num, text)], source_name=path.name)
				chunks = (
					splitter.chunk(page_markdown)
					if chunking_strategy == "semantic"
					else splitter.split_text(page_markdown)
				)
				if chunks:
					page_metadatas = [{**metadata, "chunk": i} for i in range(len(chunks))]
					self._vectorstore.add_texts(chunks, metadatas=page_metadatas)
					total_chunks += len(chunks)

			log_success(f"Indexed {total_chunks} chunks from PDF: {path.name}")
			return f"Successfully indexed {total_chunks} chunks from {path.name}"
		except Exception as e:
			log_error(f"Failed to read PDF file: {e}")
			raise

	def _ingest_json_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			text = self._read_text_utf8(path)
			if not text.strip():
				raise ValueError("JSON file is empty")
			try:
				data = json.loads(text)
			except json.JSONDecodeError:
				data = self._parse_json_lines(text)
				if data is None:
					raise ValueError("Invalid JSON/JSONL format")

			if data in ({}, [], None, ""):
				raise ValueError("JSON file contains no data")

			markdown = MarkdownFormatter.json_to_markdown(data)
			return self.add_document(
				markdown,
				source=source_name or str(path),
				metadata=metadata,
				chunking_strategy=chunking_strategy,
			)
		except Exception as e:
			log_error(f"Failed to read JSON file: {e}")
			raise

	def _ingest_csv_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			text = self._read_text_utf8(path)
			if not text.strip():
				raise ValueError("CSV file is empty")
			sample = text[:4096]
			sniffer = csv.Sniffer()
			try:
				dialect = sniffer.sniff(sample)
			except Exception:
				dialect = csv.excel

			rows = []
			reader = csv.reader(io.StringIO(text), dialect)
			for row in reader:
				rows.append([cell.strip() for cell in row])

			non_empty_rows = [r for r in rows if any(cell for cell in r)]
			if not non_empty_rows:
				raise ValueError("CSV file contains no data")

			markdown = MarkdownFormatter.csv_to_markdown(non_empty_rows)
			return self.add_document(
				markdown,
				source=source_name or str(path),
				metadata=metadata,
				chunking_strategy=chunking_strategy,
			)
		except Exception as e:
			log_error(f"Failed to read CSV file: {e}")
			raise

	def _ingest_html_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			content = self._read_text_utf8(path)
			if not content.strip():
				raise ValueError("HTML file is empty")
			markdown = MarkdownFormatter.html_to_markdown(content)
			return self.add_document(
				markdown,
				source=source_name or str(path),
				metadata=metadata,
				chunking_strategy=chunking_strategy,
			)
		except Exception as e:
			log_error(f"Failed to read HTML file: {e}")
			raise

	def _ingest_docx_file(
		self,
		path: Path,
		chunking_strategy: str,
		*,
		source_name: Optional[str] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> str:
		try:
			from docx import Document as DocxDocument

			doc = DocxDocument(str(path))
			paragraphs = [p.text for p in doc.paragraphs if p.text]
			markdown = MarkdownFormatter.docx_to_markdown(paragraphs)
			return self.add_document(
				markdown,
				source=source_name or str(path),
				metadata=metadata,
				chunking_strategy=chunking_strategy,
			)
		except Exception as e:
			log_error(f"Failed to read DOCX file: {e}")
			raise

	def _validate_file_size(self, path: Path) -> None:
		try:
			size_mb = path.stat().st_size / (1024 * 1024)
			if size_mb > self.max_file_mb:
				raise ValueError(
					f"File size {size_mb:.2f}MB exceeds limit of {self.max_file_mb:.2f}MB"
				)
		except Exception as e:
			log_error(f"File size validation failed for {path.name}: {e}")
			raise

	def _read_text_utf8(self, path: Path) -> str:
		"""Read text using UTF-8 (with BOM support)."""
		try:
			return path.read_text(encoding="utf-8-sig")
		except Exception as e:
			raise ValueError(f"Unsupported encoding or unreadable file: {e}")

	def _parse_json_lines(self, text: str) -> Optional[Any]:
		"""Attempt to parse JSON Lines; return None if parsing fails."""
		lines = [line.strip() for line in text.splitlines() if line.strip()]
		if not lines:
			return None
		items = []
		try:
			for line in lines:
				items.append(json.loads(line))
			return items
		except Exception:
			return None
