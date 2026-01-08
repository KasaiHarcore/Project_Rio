import os

from app.model import form
from app.model.router import register_all_models
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from app.api.openai import OpenAIModel
from app.api.openrouter import OpenRouterModel

from app.log import log_success, log_error, log_warning

# Global database connection
db_connection = None

def _ensure_models_registered() -> None:
	if form.get_all_model_names():
		return
	register_all_models()
 
def get_available_models():
	"""
	Get list of available models based on which API keys are set.
	Only shows models for providers that have API keys configured.
	"""
	available = []
	openai_key = os.getenv("OPENAI_API_KEY", "").strip()
	openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
	
	for model_name, model in form.MODEL_HUB.items():
		if isinstance(model, OpenAIModel) and openai_key:
			available.append(model_name)
		elif isinstance(model, OpenRouterModel) and openrouter_key:
			available.append(model_name)
	
	return available


def _reset_cost_counters() -> None:
	form._init_thread_cost()
	form.thread_cost.process_cost = 0.0
	form.thread_cost.process_input_tokens = 0
	form.thread_cost.process_output_tokens = 0

def on_clear():
	"""Clear UI fields and reset counters."""
	_reset_cost_counters()
	log_success("Cleared fields and reset counters")
	return "", "", "", ""


def on_set_api_keys(openai_key: str, openrouter_key: str) -> str:
	"""Set API keys from user input."""
	message_parts = []
	
	if openai_key and openai_key.strip():
		os.environ["OPENAI_API_KEY"] = openai_key.strip()
		log_success("OpenAI API key set")
		message_parts.append("OpenAI API key set")
	else:
		# Clear the key if empty
		os.environ.pop("OPENAI_API_KEY", None)
		if openai_key == "":  # User explicitly cleared it
			message_parts.append("OpenAI API key removed")
	
	if openrouter_key and openrouter_key.strip():
		os.environ["OPENROUTER_API_KEY"] = openrouter_key.strip()
		log_success("OpenRouter API key set")
		message_parts.append("OpenRouter API key set")
	else:
		# Clear the key if empty
		os.environ.pop("OPENROUTER_API_KEY", None)
		if openrouter_key == "":  # User explicitly cleared it
			message_parts.append("OpenRouter API key removed")
	
	if not message_parts:
		log_error("No API keys provided")
		return "No API keys provided"
	
	return " | ".join(message_parts)

def on_connect_database(db_uri: str) -> str:
	"""Connect to a SQL database."""
	global db_connection
	
	db_uri = (db_uri or "").strip()
	
	if not db_uri:
		log_error("Database URI is required")
		return "Database URI is required"
	
	try:
		db_connection = SQLDatabase.from_uri(db_uri)
		tables = db_connection.get_usable_table_names()
		log_success(f"Connected to database. Available tables: {tables}")
		return f"Connected successfully!\n\nAvailable tables: {', '.join(tables)}"
	except Exception as e:
		log_error(f"Database connection failed: {str(e)}")
		return f"Connection failed: {str(e)}"


def create_sql_query_tool():
	"""Create a langchain tool for executing SQL queries."""
	@tool
	def execute_sql_query(query: str) -> str:
		"""
		Execute a SQL query on the connected database and return the results.
		"""
		global db_connection
		
		if db_connection is None:
			return "Error: No database connected. Please connect to a database first."
		
		# Basic safety check - only allow SELECT queries
		query_upper = query.strip().upper()
		if not query_upper.startswith("SELECT"):
			return "Error: Only SELECT queries are allowed for safety reasons."
		
		try:
			result = db_connection.run(query)
			log_info(f"SQL Query executed: {query}")
			log_info(f"Result: {result}")
			return str(result)
		except Exception as e:
			error_msg = f"SQL execution error: {str(e)}"
			log_error(error_msg)
			return error_msg
	
	return execute_sql_query