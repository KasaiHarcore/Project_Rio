"""Graph Vector Store tool for structured data retrieval and analysis"""

from __future__ import annotations

import os
import atexit
from typing import Optional, Dict, Any, Tuple

from backend.utils.log import log_info, log_success, log_error, log_warning
from langchain_neo4j import Neo4jGraph
