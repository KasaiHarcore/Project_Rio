"""
Note Retrieval Worker — Searches and retrieves from the user's note knowledge base.

This worker is triggered by the supervisor when the conversation requires
information that might exist in the user's notes, collections, or note graph.

Unlike the existing NoteWorker (which *creates* notes), this worker *reads*
from the note system using semantic search + graph traversal.
"""

from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

from workflows.workers.base import BaseWorker
from workflows.state import AgentState, WorkerResult, WorkerType
from utils.log import log_info, log_warning

if TYPE_CHECKING:
    from core.settings import AgentConfig


NOTE_RETRIEVAL_SYSTEM_PROMPT = """I am the Note Retrieval module. I search through Sensei's personal notes, collections, and knowledge graph to find relevant information.

Guidelines:
- I use semantic search to find notes most relevant to the query.
- I traverse the note graph to find related notes (linked notes, backlinks).
- I present findings with note titles, content excerpts, and link relationships.
- If no relevant notes exist, I say so clearly.
- I never fabricate note content.

Output Format:
I present the relevant notes clearly, with titles and relationship context.
"""


class NoteRetrievalWorker(BaseWorker):
    """Worker that searches the user's note knowledge base.

    Uses the NoteKnowledgeTool to:
    1. Semantic search via Qdrant vector store
    2. Graph traversal via NoteLink relationships
    3. Collection-scoped filtering
    """

    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.NOTE_RETRIEVAL

    @property
    def name(self) -> str:
        return "Note Retrieval Worker"

    @property
    def description(self) -> str:
        return "Searches the user's notes, collections, and knowledge graph for relevant information"

    @property
    def system_prompt(self) -> str:
        return NOTE_RETRIEVAL_SYSTEM_PROMPT

    def __init__(self, config: Optional["AgentConfig"] = None, top_k: int = 10):
        super().__init__(config=config)
        self.top_k = top_k

    def _get_knowledge_tool(self):
        """Get the NoteKnowledgeTool with a fresh DB session."""
        from infrastructure.database.session import SessionLocal
        from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool
        db = SessionLocal()
        return NoteKnowledgeTool(db), db

    def _execute(self, state: AgentState) -> WorkerResult:
        """Search the note knowledge base."""
        question = self.get_question(state)
        user_id = state.get("user_id")

        if not user_id:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No user_id in state — cannot search notes.",
            )

        if not question:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No question provided for note search.",
            )

        last_reasoning = self.get_last_decision_reasoning(state)
        operation = self._determine_operation(question, last_reasoning)

        tool = None
        db = None
        try:
            tool, db = self._get_knowledge_tool()
            result = self._dispatch(tool, operation, user_id, question)

            if not result:
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content="No relevant notes found for this query.",
                    metadata={"operation": operation, "num_results": 0},
                )

            formatted = self._format_results(operation, result)

            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=formatted,
                metadata={
                    "operation": operation,
                    "raw_results": result,
                },
            )
        except Exception as e:
            log_warning(f"Note retrieval failed: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=str(e),
            )
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass

    def _determine_operation(self, question: str, reasoning: str) -> str:
        """Determine which note operation to perform."""
        combined = f"{question} {reasoning}".lower()

        if any(w in combined for w in ["collection", "folder", "group"]):
            if any(w in combined for w in ["list", "show", "what"]):
                return "list_collections"
            return "search_notes"

        if any(w in combined for w in ["graph", "linked", "connected", "relationship"]):
            return "get_note_graph"

        if any(w in combined for w in ["backlink", "reference", "who links", "pointing to"]):
            return "get_backlinks"

        return "search_notes"

    def _dispatch(self, tool, operation: str, user_id: str, question: str) -> str:
        """Dispatch to the appropriate NoteKnowledgeTool method."""
        log_info(f"Note retrieval: operation={operation}, query={question[:80]}")

        if operation == "list_collections":
            return tool.list_collections(user_id)
        elif operation == "get_note_graph":
            return tool.get_note_graph(user_id)
        elif operation == "get_backlinks":
            return tool.search_notes(question, user_id, k=self.top_k)
        else:
            return tool.search_notes(question, user_id, k=self.top_k)

    def _format_results(self, operation: str, raw_result: str) -> str:
        """Format raw JSON results into readable text for the LLM."""
        try:
            data = json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            return raw_result

        if operation == "list_collections":
            if not data:
                return "No collections found."
            lines = ["## Note Collections\n"]
            for col in data:
                lines.append(f"- **{col['name']}** ({col['note_count']} notes) [id: {col['id']}]")
            return "\n".join(lines)

        if operation == "get_note_graph":
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            stats = data.get("stats", {})
            lines = [
                "## Note Graph\n",
                f"Nodes: {stats.get('total_nodes', len(nodes))} | "
                f"Edges: {stats.get('total_edges', len(edges))} | "
                f"Notes: {stats.get('total_notes', 0)}\n",
            ]
            if nodes:
                lines.append("### Nodes")
                for n in nodes[:20]:
                    lines.append(f"- [{n['type']}] {n['label']}")
            if edges:
                lines.append("\n### Connections")
                for e in edges[:20]:
                    lines.append(f"- {e.get('label', 'linked')}")
            return "\n".join(lines)

        # Default: search results
        if not data:
            return "No matching notes found."

        lines = ["## Retrieved Notes\n"]
        for i, note in enumerate(data, 1):
            score = note.get("score", "")
            score_str = f" (relevance: {score})" if score else ""
            lines.append(f"### Note {i}: {note.get('title', 'Untitled')}{score_str}")
            if note.get("is_important"):
                lines.append("*Important note*")
            content = note.get("content", "")
            if content:
                lines.append(f"\n{content}\n")
            lines.append(f"*Source: {note.get('source', 'user')} | ID: {note.get('id', '')}*\n")
        return "\n".join(lines)
