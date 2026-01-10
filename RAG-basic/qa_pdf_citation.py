from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Any, List
from langchain_core.documents import Document

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
	sys.path.insert(0, str(PROJECT_DIR))


from app.log import log_success, log_error, log_warning
from app.model import form
from app.utils import on_clear, on_set_api_keys, _ensure_models_registered, _reset_cost_counters, get_available_models
from database.chroma import get_splitter, get_vectordb
from pypdf import PdfReader


def _sanitize_pdf_for_pypdf(file_path: str) -> str:
	"""Some PDFs contain leading bytes/newlines before '%PDF'.
	This creates a sanitized copy when needed so parsers don't choke.
	"""
	try:
		with open(file_path, "rb") as f:
			head = f.read(2048)
		pos = head.find(b"%PDF")
		if pos <= 0:
			return file_path
		# Create a trimmed copy starting at the %PDF marker
		tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_path).suffix or ".pdf")
		tmp_path = tmp.name
		tmp.close()
		with open(file_path, "rb") as src, open(tmp_path, "wb") as dst:
			src.seek(pos)
			shutil.copyfileobj(src, dst)
		return tmp_path
	except Exception:
		# Best effort: if sanitize fails, fall back to original path.
		return file_path

def load_pdf(file_path: str) -> List[Document]:
	# Use pypdf directly with strict=False to handle more real-world PDFs.
	# Also sanitize the header if it contains leading bytes before %PDF.
	sanitized_path = _sanitize_pdf_for_pypdf(file_path)
	reader = PdfReader(sanitized_path, strict=False)
	pages: List[Document] = []
	for i, page in enumerate(reader.pages):
		text = page.extract_text() or ""
		pages.append(
			Document(
				page_content=text,
				metadata={
					"source": file_path,
					"page": i,
				},
			)
		)
	return pages

def ingest_pdf(file_path: str) -> int:
	"""
	Load PDF → chunk → store in Chroma
	"""
	docs = load_pdf(file_path)
	chunks = get_splitter().split_documents(docs)

	get_vectordb().add_documents(chunks)
	return len(chunks)

def retrieve(query: str, k: int = 4) -> List[Document]:
	return get_vectordb().similarity_search(query, k=k)


def _format_citations(docs: List[Document]) -> str:
	items = []
	for d in docs or []:
		md = dict(getattr(d, "metadata", {}) or {})
		items.append(
			{
				"source": md.get("source"),
				"page": md.get("page"),
				"start_index": md.get("start_index"),
			}
		)
	return json.dumps(items, indent=2)


def on_ingest_pdf(pdf_file: str | None) -> str:
	"""Ingest a user-uploaded PDF into Chroma."""
	if not pdf_file:
		log_error("No PDF file provided")
		return "Error: Please upload a PDF file first."

	try:
		log_success(f"Ingesting PDF: {pdf_file}")
		chunk_count = ingest_pdf(pdf_file)
		# Persist if the vector store supports it
		persist_fn = getattr(get_vectordb(), "persist", None)
		if callable(persist_fn):
			persist_fn()
		log_success(f"Ingest completed: {chunk_count} chunks")
		return f"Ingested successfully: {chunk_count} chunks"
	except Exception as e:
		log_error(f"Ingest error: {type(e).__name__}: {str(e)}")
		return f"Error ingesting PDF: {type(e).__name__}: {str(e)}"


def on_pdf_query(input_text: str, system_prompt: str):
	"""
	Answering user question with database search
	"""
	input_text = (input_text or "").strip()

	# Validate inputs
	if not input_text:
		log_error("No input text provided")
		error_stats = {"error": "No input text", "error_type": "ValidationError"}
		return "Please provide a question.", "[]", json.dumps(error_stats, indent=2)

	extra_info = retrieve(input_text, 4)
	context_text = "\n\n".join([f"[{i+1}] {d.page_content}" for i, d in enumerate(extra_info or [])])

	user_prompt = f"""**Retrieved Context**
{context_text}

	**Input Text:**
	{input_text}"""

	try:
		log_success("Starting LLM invocation...")
		log_success(f"Model: {form.SELECTED_MODEL.name}")
		
		response_text = form.SELECTED_MODEL.call(
			system_prompt=system_prompt,
			user_prompt=user_prompt,
			return_text=True
		)
		log_success("LLM invocation completed successfully")
		
		stats = form.SELECTED_MODEL.get_overall_exec_stats()
		return str(response_text), _format_citations(extra_info), json.dumps(stats, indent=2)
		
	except KeyboardInterrupt:
		log_error("Operation cancelled by user")
		raise

	except Exception as e:
		log_error(f"Error during LLM invocation: {type(e).__name__}: {str(e)}")
		error_msg = "Error during extraction, check logs for details."
		error_stats = {
			"error": str(e),
			"error_type": type(e).__name__,
			"model": form.SELECTED_MODEL.name if hasattr(form, 'SELECTED_MODEL') else "Unknown"
		}
		return error_msg, "[]", json.dumps(error_stats, indent=2)


def build_demo() -> gr.Blocks:
	_ensure_models_registered()
	if not hasattr(form, "SELECTED_MODEL") or form.SELECTED_MODEL is None:
		first = form.get_all_model_names()[0]
		form.set_model(first)
	
	# Initialize cost counters to avoid AttributeError
	_reset_cost_counters()

	all_model_names = form.get_all_model_names()
	available_model_names = get_available_models()
	
	# If no models available, use all models (for initial state)
	initial_models = available_model_names if available_model_names else all_model_names

	with gr.Blocks(title="PDF Q&A AI") as demo:
		gr.Markdown(
			"""# PDF Q&A AI"""
		)

		with gr.Accordion("Upload PDF", open=True):
			with gr.Row():
				pdf_file = gr.File(
					label="Upload PDF",
					file_types=[".pdf"],
					type="filepath",
				)
				ingest_btn = gr.Button("Ingest PDF", variant="primary")
			pdf_ingest_status = gr.Textbox(
				label="Ingest Status",
				value="No PDF ingested yet",
				interactive=False,
			)
		
		with gr.Accordion("API Key Settings", open=True):
			with gr.Row():
				openai_key_input = gr.Textbox(
					label="OpenAI API Key",
					placeholder="sk-...",
					type="password",
					value=os.getenv("OPENAI_API_KEY", ""),
				)
				openrouter_key_input = gr.Textbox(
					label="OpenRouter API Key",
					placeholder="sk-or-...",
					type="password",
					value=os.getenv("OPENROUTER_API_KEY", ""),
				)
			
			with gr.Row():
				set_keys_btn = gr.Button("Set API Keys", variant="primary")
				api_status = gr.Textbox(
					label="Status",
					value="No API keys set yet" if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY") else "API keys loaded from environment",
					interactive=False,
				)

		with gr.Row():
			model_dropdown = gr.Dropdown(
				choices=initial_models,
				value=getattr(form.SELECTED_MODEL, "name", initial_models[0]) if initial_models else all_model_names[0],
				label="Model",
			)
		

		system_text = gr.Textbox(
				label="System",
				value="""You are an helpful AI assistant.
Your task is to answer the user's question using ONLY the information provided in the retrieved context.
Do not use prior knowledge or assumptions outside of the given context.
If the context does not contain enough information to answer the question, clearly state that you do not have sufficient information.
DO NOT MAKE UP FACTS OR SPECULATE"""
		)

		input_text = gr.Textbox(
				label="Question",
				placeholder="What do you want to know about?",
				lines=3,
		)
		
		with gr.Row():
			query_btn = gr.Button("Execute Query", variant="primary", size="lg")
			clear_btn = gr.Button("Clear", size="lg")
  
		chat_answer = gr.Textbox(
			label="AI Answer",
			lines=5,
			interactive=False,
		)
  
		citation_links = gr.Textbox(
			label="Citations",
			lines=3,
			interactive=False,
		)
		
		stats = gr.Textbox(label="Run Stats", lines=6, interactive=False)

		def update_model_choices_after_keys(openai_key, openrouter_key):
			"""Update available models after API keys are set"""
			available = get_available_models()
			if not available:
				# If still no keys, show all models
				available = form.get_all_model_names()
			
			# Set to first available model
			if available:
				form.set_model(available[0])
			
			return gr.Dropdown(choices=available, value=available[0] if available else form.get_all_model_names()[0])

		# Event handlers
		set_keys_btn.click(
			fn=on_set_api_keys,
			inputs=[openai_key_input, openrouter_key_input],
			outputs=[api_status],
		).then(
			fn=update_model_choices_after_keys,
			inputs=[openai_key_input, openrouter_key_input],
			outputs=[model_dropdown],
		)

		model_dropdown.change(
			fn=lambda model_name: form.set_model(model_name),
			inputs=[model_dropdown],
			outputs=[],
		)

		ingest_btn.click(
			fn=on_ingest_pdf,
			inputs=[pdf_file],
			outputs=[pdf_ingest_status],
		)

		query_btn.click(
			fn=on_pdf_query,
			inputs=[input_text, system_text],
			outputs=[chat_answer, citation_links, stats],
		)
		
		input_text.submit(
			fn=on_pdf_query,
			inputs=[input_text, system_text],
			outputs=[chat_answer, citation_links, stats],
		)

		clear_btn.click(
			fn=on_clear,
			inputs=[],
			outputs=[input_text, chat_answer, citation_links, stats],
		)

		demo.load(
			fn=lambda: json.dumps(form.SELECTED_MODEL.get_overall_exec_stats(), indent=2),
			outputs=stats,
		)

	return demo


def _launch_gradio(demo: gr.Blocks) -> None:
	host = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
	port = int(os.getenv("GRADIO_SERVER_PORT", "7861"))
	share_env = os.getenv("GRADIO_SHARE", "").strip().lower()
	share = share_env in {"1", "true", "yes", "y", "on"}

	# Launch port busy check
	ports_to_try = list(range(port, port + 21))
 
	log_success("PDF Q&A AI Application Initialize! All the app setup and run time will report here")

	last_exc = None
	for p in ports_to_try:
		try:
			demo.launch(server_name=host, server_port=p, share=share)
			return
		except ValueError as e:
			# Common in remote/WSL/container contexts
			if "localhost is not accessible" in str(e) and not share:
				log_warning("Retrying Gradio launch with share=True")
				share = True
				last_exc = e
				continue
			raise
		except OSError as e:
			# Port in use
			last_exc = e
			continue

	if last_exc:
		raise last_exc


if __name__ == "__main__":
	_launch_gradio(build_demo())