from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
	sys.path.insert(0, str(PROJECT_DIR))

from app.log import log_success, log_error, log_warning
from app.model import form
from app.utils import on_clear, on_set_api_keys, _ensure_models_registered, _reset_cost_counters, get_available_models

def on_summarize_text(input_text: str, summary_instruction: str):
	"""
	Summarize the input text based on user's instruction.
	"""
	input_text = (input_text or "").strip()
	summary_instruction = (summary_instruction or "").strip()
	
	if not summary_instruction:
		summary_instruction = "Summarize the following text in a concise and clear manner."
	
	system_prompt = """You are an expert at summarizing long texts into concise and clear summaries.
Your task is to analyze the provided text and generate a summary based on the user's instruction.
Return the summary as plain text."""
	
	user_prompt = f"""**Summary Task:** {summary_instruction}
 
					**Input Text:**
					{input_text}"""
	
	try:
		log_success("Starting LLM invocation...")
		log_success(f"Model: {form.SELECTED_MODEL.name}")
		
		response_text = form.SELECTED_MODEL.call(
			[],
			system_prompt=system_prompt,
			user_prompt=user_prompt,
			return_text=True,
		)
		log_success("LLM invocation completed successfully")
		
		stats = form.SELECTED_MODEL.get_overall_exec_stats()
		return str(response_text), json.dumps(stats, indent=2)
		
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
		return error_msg, json.dumps(error_stats, indent=2)

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

	with gr.Blocks(title="Text Summarizer") as demo:
		gr.Markdown(
			"""# Text Summarizer"""
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

		summary_instruction = gr.Textbox(
			label="Summary Instruction",
			placeholder="How do you want the text summarized?",
			lines=2,
		)
		
		gr.Examples(
			label="Summary Examples",
			examples=[
				["Summarize the text in bullet points"],
				["Provide a one-paragraph summary of the text"],
			],
			inputs=summary_instruction
		)

		input_text = gr.Textbox(
			label="Input Text",
			placeholder="Paste the text you want summarized...",
			lines=10,
		)

		with gr.Row():
			summarize_btn = gr.Button("Summarize", variant="primary", size="lg")
			clear_btn = gr.Button("Clear", size="lg")

		output_text = gr.Textbox(
			label="Summary",
			lines=12,
			interactive=False,
		)

		stats = gr.Textbox(label="Run stats", lines=8, interactive=False)
  
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

		summarize_btn.click(
			fn=on_summarize_text,
			inputs=[input_text, summary_instruction],
			outputs=[output_text, stats],
		)

		input_text.submit(
			fn=on_summarize_text,
			inputs=[input_text, summary_instruction],
			outputs=[output_text, stats],
		)

		clear_btn.click(
			fn=on_clear,
			inputs=[],
			outputs=[input_text, summary_instruction, output_text, stats],
		)

		demo.load(
			fn=lambda: json.dumps(form.SELECTED_MODEL.get_overall_exec_stats(), indent=2),
			outputs=stats,
		)

	return demo

def _launch_gradio(demo: gr.Blocks) -> None:
	host = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
	port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
	share_env = os.getenv("GRADIO_SHARE", "").strip().lower()
	share = share_env in {"1", "true", "yes", "y", "on"}

	# Launch port busy check
	ports_to_try = list(range(port, port + 21))
 
	log_success("Application Initialize! All the app setup and run time will report here")

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
