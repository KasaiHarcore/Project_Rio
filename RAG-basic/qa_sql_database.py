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
from database.db import db_manager

def on_connect_database(host: str, port: str, database: str, user: str, password: str):
	"""
	Connect to PostgreSQL database.
	"""
	host = (host or "").strip()
	port = (port or "5432").strip()
	database = (database or "postgres").strip()
	user = (user or "postgres").strip()
	password = (password or "").strip()
	
	try:
		log_success(f"Attempting to connect to database: {database} at {host}:{port}")
		success = db_manager.connect(host, port, database, user, password)
		
		if success:
			log_success("Database connected successfully!")
			# Get schema info
			schema, error = db_manager.get_table_schema()
			if error:
				return f"Connected but schema error: {error}", ""
			return "Database connected", schema
		else:
			log_error("Database connection failed")
			return "Connection failed", ""
	
	except Exception as e:
		log_error(f"Connection error: {type(e).__name__}: {str(e)}")
		return f"Error: {str(e)}", ""


def on_get_schema(table_name: str = ""):
	"""
	Get database schema information.
	"""
	table_name = (table_name or "").strip()
	
	try:
		if table_name:
			log_success(f"Fetching schema for table: {table_name}")
			schema, error = db_manager.get_table_schema(table_name)
		else:
			log_success("Fetching schema for all tables")
			schema, error = db_manager.get_table_schema()
		
		if error:
			log_error(f"Schema error: {error}")
			return f"Error: {error}"
		
		return schema if schema else "No tables found in database"
	
	except Exception as e:
		log_error(f"Schema retrieval error: {type(e).__name__}: {str(e)}")
		return f"Error: {str(e)}"


def on_query_with_ai(natural_language_query: str, schema_context: str):
	"""
	Generate and execute SQL query based on natural language input using AI.
	"""
	natural_language_query = (natural_language_query or "").strip()
	schema_context = (schema_context or "").strip()
	
	if not natural_language_query:
		log_warning("Empty query received")
		return "Please enter a query.", "", ""
	
	if not schema_context:
		log_warning("No schema context available")
		return "Please connect to database first to get schema.", "", ""
	
	# Step 1: Generate SQL using AI
	system_prompt = """You are an expert PostgreSQL database assistant. Your task is to convert natural language queries into valid PostgreSQL SQL queries.

IMPORTANT RULES:
1. Return ONLY the SQL query, nothing else
2. Do not include markdown formatting, code blocks, or explanations
3. Use proper PostgreSQL syntax
4. Generate safe, read-only SELECT queries unless explicitly asked otherwise
5. Do not use semicolon at the end"""

	user_prompt = f"""Based on the following database schema, generate a PostgreSQL SQL query for this request:

**Database Schema:**
{schema_context}

**User Request:**
{natural_language_query}

Return ONLY the SQL query without any formatting or explanation."""
	
	try:
		log_success("Generating SQL query with AI...")
		log_success(f"Model: {form.SELECTED_MODEL.name}")
		
		sql_query = form.SELECTED_MODEL.call(
			system_prompt=system_prompt,
			user_prompt=user_prompt,
			return_text=True,
		)
		
		# Clean up the generated SQL
		sql_query = str(sql_query).strip()
		# Remove markdown code blocks if present
		if sql_query.startswith('```'):
			sql_query = sql_query.split('```')[1]
			if sql_query.startswith('sql'):
				sql_query = sql_query[3:]
			sql_query = sql_query.strip()
		
		log_success(f"Generated SQL: {sql_query}")
		
		# Step 2: Execute the generated SQL
		log_success("Executing generated SQL query...")
		results, error = db_manager.execute_query(sql_query)
		
		if error:
			log_error(f"Query execution error: {error}")
			stats = form.SELECTED_MODEL.get_overall_exec_stats()
			return sql_query, f"Query Error: {error}", json.dumps(stats, indent=2)
		
		log_success(f"Query executed successfully! Returned {len(results)} rows")
		
  
		answer_prompt = f"""Based on the following SQL query results, provide a concise answer to the user's original request.
**SQL Query:**
{sql_query}

**Query Results:**
{results}

**User Request:**
{natural_language_query}
Provide a clear and concise answer based on the results."""
		
		try:
			log_success("Generating answer with AI based on query results...")
			chat_answer = form.SELECTED_MODEL.call(
				system_prompt=system_prompt,
				user_prompt=answer_prompt,
				return_text=True,
			)
			log_success("Answer generated successfully!")
		except Exception as e:
			log_error(f"Error generating answer: {type(e).__name__}: {str(e)}")
			chat_answer = "No answer returned due to error"
  
		# Format results
		if results:
			results_text = json.dumps(results, indent=2, default=str)
		else:
			results_text = "Query executed successfully but returned no results."
		
		stats = form.SELECTED_MODEL.get_overall_exec_stats()
		return sql_query, results_text, chat_answer, json.dumps(stats, indent=2)
	
	except KeyboardInterrupt:
		log_error("Operation cancelled by user")
		raise
	
	except Exception as e:
		log_error(f"Error during AI query: {type(e).__name__}: {str(e)}")
		error_stats = {
			"error": str(e),
			"error_type": type(e).__name__,
			"model": form.SELECTED_MODEL.name if hasattr(form, 'SELECTED_MODEL') else "Unknown"
		}
		return "", f"Error: {str(e)}", json.dumps(error_stats, indent=2)


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

	with gr.Blocks(title="SQL Query AI") as demo:
		gr.Markdown(
			"""# SQL Query AI"""
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

		gr.Markdown("## Database Connection")
		
		with gr.Row():
			with gr.Column():
				db_host = gr.Textbox(
					label="Host",
					value=os.getenv("POSTGRES_HOST", "localhost"), # Check by ip route | grep default
					placeholder="localhost"
				)
				db_port = gr.Textbox(
					label="Port",
					value=os.getenv("POSTGRES_PORT", "5432"), # Default PostgreSQL port
					placeholder="5432"
				)
			with gr.Column():
				db_name = gr.Textbox(
					label="Database",
					value=os.getenv("POSTGRES_DB", "postgres"),
					placeholder="postgres"
				)
				db_user = gr.Textbox(
					label="User",
					value=os.getenv("POSTGRES_USER", "postgres"),
					placeholder="postgres"
				)
		
		db_password = gr.Textbox(
			label="Password",
			type="password",
			value=os.getenv("POSTGRES_PASSWORD", ""),
			placeholder="Enter database password"
		)
		
		with gr.Row():
			connect_btn = gr.Button("Connect to Database", variant="primary", size="lg")
			get_schema_btn = gr.Button("Refresh Schema", size="lg")
		
		connection_status = gr.Textbox(
			label="Connection Status",
			value="Not connected",
			interactive=False,
		)
		
		schema_output = gr.Textbox(
			label="Database Schema",
			lines=10,
			interactive=False,
			placeholder="Connect to database to see schema..."
		)
		
		gr.Markdown("## AI-Powered Query")
		
		natural_query = gr.Textbox(
			label="Natural Language Query",
			placeholder="e.g., Show me all users who registered in the last 7 days",
			lines=3,
		)
		
		with gr.Row():
			query_btn = gr.Button("Generate & Execute Query", variant="primary", size="lg")
		
		generated_sql = gr.Textbox(
			label="Generated SQL Query",
			interactive=False,
		)
		
		query_results = gr.Textbox(
			label="Query Results",
			lines=5,
			interactive=False,
		)
  
		chat_answer = gr.Textbox(
			label="AI Answer",
			lines=5,
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

		connect_btn.click(
			fn=on_connect_database,
			inputs=[db_host, db_port, db_name, db_user, db_password],
			outputs=[connection_status, schema_output],
		)
		
		get_schema_btn.click(
			fn=on_get_schema,
			inputs=[],
			outputs=[schema_output],
		)

		query_btn.click(
			fn=on_query_with_ai,
			inputs=[natural_query, schema_output],
			outputs=[generated_sql, query_results, chat_answer, stats],
		)
		
		natural_query.submit(
			fn=on_query_with_ai,
			inputs=[natural_query, schema_output],
			outputs=[generated_sql, query_results, chat_answer, stats],
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
 
	log_success("SQL Query AI Application Initialize! All the app setup and run time will report here")

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
