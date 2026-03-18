from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from utils.log import log_info, log_warning
from workflows.state import WorkerResult, WorkerType

if TYPE_CHECKING:
    from core.settings import AgentConfig


# ═══════════════════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════════════════

class NoteState(TypedDict, total=False):
    """Internal state for the unified note subgraph."""

    # ── Inputs (set by the entry adapter) ────────────────────────
    question: str
    context: str            # gathered_context from parent (for CREATE)
    history: str
    user_id: Optional[str]
    thread_id: Optional[str]  # current conversation thread (for CREATE)

    # ── Intermediate ─────────────────────────────────────────────
    collections_summary: str
    collections_raw: List[Dict[str, Any]]

    intent: str             # CREATE | SEARCH | ... | REASON
    intent_data: Dict[str, Any]

    # ── Output ───────────────────────────────────────────────────
    result: Optional[Dict[str, Any]]


# ═══════════════════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════════════════

INTENT_PROMPT = """You are the Note module classifier.

Sensei said: "{question}"

Recent conversation:
{history}

Gathered context from other workers:
{context}

Available note collections:
{collections_summary}

Pick ONE intent:
- CREATE → The conversation produced actionable insights, study plans, TODO steps, or structured content worth extracting as sticky notes. The supervisor explicitly asked to create/extract notes. Also when gathered context from previous workers contains substantial material.
- SEARCH → Sensei wants to find notes by topic, keyword, or content. "what did I write about…", "find my notes on…", "do I have notes about…"
- GET_NOTE → Sensei wants full detail of a specific note by title or ID. "show me my note called…", "open note X"
- LIST_COLLECTIONS → Sensei wants to see their note folders/collections. "what collections do I have?", "show my note groups"
- COLLECTION_NOTES → Sensei wants notes inside a specific collection. "show notes in my Backend folder"
- GET_GRAPH → Sensei wants to see how notes are connected. "how are my notes linked?", "show note graph"
- GET_BACKLINKS → Sensei wants to see what references a specific note. "what links to this note?"
- UPDATE → Sensei wants to modify an existing note: pin/unpin, mark important, move to a collection, change content. "pin my React note", "move this note to Backend collection", "mark my Docker note as important"
- DELETE → Sensei wants to remove a note. "delete my old note about X", "remove that note"
- REASON → The question is COMPLEX and requires multiple operations to answer. Use this when the answer needs combining search + graph traversal, cross-collection analysis, path-finding between notes, centrality analysis, temporal reasoning, summarization across multiple notes, or any question that a single operation cannot answer.

Examples of REASON:
- "How are my React and Docker notes related?" → needs search + graph + path analysis
- "Which of my notes is referenced the most?" → needs full graph + degree analysis
- "Summarize everything I've learned about databases" → needs search + synthesize
- "What topics appear across my collections?" → needs list collections + notes per collection + analysis
- "What did I learn this week?" → needs temporal search + synthesis
- "Give me an overview of my knowledge graph" → needs graph + analysis

Return ONLY JSON:
{{"intent": "…", "reasoning": "one sentence", "target_note_title": "title or null", "target_note_id": "uuid or null", "target_collection_name": "name or null", "target_collection_id": "uuid or null", "search_query": "the search text or null"}}

Decision rules (in priority order):
1. If gathered context exists and question implies extracting/creating/saving notes → CREATE
2. If the question requires chaining MULTIPLE operations or sophisticated analysis → REASON
3. Explicit collection listing ("list collections", "my folders", "what groups") → LIST_COLLECTIONS
4. Notes IN a specific collection ("notes in Backend", "show Study notes") → COLLECTION_NOTES
5. Specific note by name/ID ("show note X", "open my note about…") → GET_NOTE
6. Note connections, links, relationships ("graph", "connected", "linked") → GET_GRAPH
7. What references/links to a note ("backlinks", "references", "who links") → GET_BACKLINKS
8. Modify a note ("pin", "move to collection", "mark important", "change title") → UPDATE
9. Remove a note ("delete note", "remove note") → DELETE
10. Everything else (topical search) → SEARCH"""

SEARCH_REFINEMENT_PROMPT = """You are a note search query optimizer.

Sensei's original question: "{question}"

Recent conversation for context:
{history}

Available collections:
{collections_summary}

Your job: Extract the best search query and optional collection filter.

Return ONLY JSON:
{{"query": "the optimized search text", "collection_id": "uuid or null"}}

Guidelines:
- Strip conversational filler — keep only the topic.
- If Sensei mentions a collection name, resolve it to the collection_id from the list above.
- If no collection is mentioned, set collection_id to null.
- Keep the query concise but semantically rich.
"""

NOTE_EXTRACTION_PROMPT = """I am the Note-taking module. I will analyze the conversation and extract important notes or actionable TODO items to help Sensei stay organized.

## Sensei's Question / Request
{question}

## Context (worker results, conversation so far)
{context}

## Instructions
1. Extract the most important takeaways, insights, or action items.
2. If the content suggests a step-by-step plan, study roadmap, or action list, structure it as TODO items.
3. Keep each note concise (1-3 sentences for plain notes, short phrases for TODOs).
4. Produce 1-3 notes maximum. Quality over quantity.
5. If there is nothing noteworthy, return an empty array.

## Output Format
Return a JSON array of note objects. Each note has:
- "content": string — the note text (also used as a summary for TODO notes)
- "todos": array of {{"text": string, "done": false}} — optional, include ONLY if the note is a checklist/plan

Example outputs:

Plain note:
[{{"content": "The CAP theorem states that a distributed system can only guarantee two of: Consistency, Availability, Partition tolerance."}}]

TODO note:
[{{"content": "Study plan for React hooks", "todos": [{{"text": "Read useState documentation", "done": false}}, {{"text": "Practice useEffect cleanup patterns", "done": false}}, {{"text": "Build a custom hook for form validation", "done": false}}]}}]

Now analyze and extract notes:"""

UPDATE_PROMPT = """I am the Note update module.

Sensei said: "{question}"

Available notes (from search or context):
{notes_context}

Available collections:
{collections_summary}

Your job: Identify WHICH note to update and WHAT fields to change.

Updatable fields:
- "title": string (max 500)
- "content": string (max 5000)
- "todos": array of {{"text": string, "done": true/false}} (REPLACES entire checklist)
- "pinned": true/false
- "is_important": true/false
- "collection_ids": array of collection UUID strings (REPLACES current collections)

Return ONLY JSON:
{{"target_note_id": "uuid or null", "target_note_title": "title or null", "updates": {{...only changed fields...}}}}

Rules:
- Only include fields Sensei explicitly wants to change.
- "Pin my React note" → {{"pinned": true}}
- "Mark as important" → {{"is_important": true}}
- "Move to Backend collection" → {{"collection_ids": ["<backend-collection-uuid>"]}}
- "Unpin that note" → {{"pinned": false}}
- "Mark first TODO done" → include full todos array with that item's "done" set to true
- When updating todos, you must include ALL existing todos (not just the changed one)
"""

REASON_PLAN_PROMPT = """You are the Note Reasoning module. You handle COMPLEX note questions that require multiple operations.

## Sensei's Question
{question}

## Available Operations
You can chain these operations to answer the question:
1. SEARCH(query, collection_id?) → semantic search across notes
2. GET_NOTE(note_id) → full note detail with links and backlinks
3. LIST_COLLECTIONS() → all collections with counts
4. COLLECTION_NOTES(collection_id) → all notes in a collection
5. GET_GRAPH(note_id?) → full graph or 1-hop subgraph around a note
6. GET_BACKLINKS(note_id) → all notes that reference a specific note

## Available Context
Collections: {collections_summary}
History: {history}

## Instructions
Create an execution plan: an ordered list of operations to run.
Think about what information you need and in what order.

Return ONLY JSON:
{{"plan": [
    {{"op": "SEARCH", "args": {{"query": "React"}}}},
    {{"op": "GET_GRAPH", "args": {{}}}},
    ...
], "reasoning": "why these operations answer the question"}}

Guidelines:
- Use the minimum operations needed. Don't over-fetch.
- For connection questions, you almost always need GET_GRAPH.
- For "most referenced" questions, GET_GRAPH gives you edge counts.
- For content-based questions, SEARCH is the primary tool.
- For cross-collection analysis, LIST_COLLECTIONS then COLLECTION_NOTES for each.
- Maximum 5 operations per plan.
"""

REASON_SYNTHESIZE_PROMPT = """You are the Note Reasoning module. Synthesize a comprehensive answer from these operation results.

## Sensei's Question
{question}

## Execution Results
{results}

## Instructions
- Directly answer Sensei's question using the data above.
- Be specific — cite note titles, collections, link counts, and relationships.
- For graph questions, describe the structure: which notes are central, which are isolated, what clusters exist.
- For connection questions, trace the path or explain why notes are related.
- For summary questions, synthesize the key themes across notes.
- Use markdown formatting for readability.
- If the data is insufficient to fully answer, say what's missing.
"""


# ═══════════════════════════════════════════════════════════════════════════
# LLM helper
# ═══════════════════════════════════════════════════════════════════════════

def _call_llm(user_prompt: str, system: str = "", config: Optional["AgentConfig"] = None) -> str:
    from infrastructure.llm import form
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    if not system:
        system = (
            "I am the Note module. I always return valid JSON. "
            "I never include commentary outside the JSON."
        )
    llm = form.SELECTED_MODEL.llm
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_prompt)])
    if isinstance(resp, AIMessage):
        return str(resp.content)
    return str(resp)


# ═══════════════════════════════════════════════════════════════════════════
# JSON parsers
# ═══════════════════════════════════════════════════════════════════════════

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = text.replace("```", "").strip()
    return text


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = _strip_fences(raw)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_json_array(raw: str) -> List[Dict[str, Any]]:
    text = _strip_fences(raw)
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


# ═══════════════════════════════════════════════════════════════════════════
# Knowledge tool access
# ═══════════════════════════════════════════════════════════════════════════

def _get_knowledge_tool():
    from infrastructure.database.session import SessionLocal
    from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool
    db = SessionLocal()
    return NoteKnowledgeTool(db), db


def _get_note_service(db):
    from repositories.note_repository import NoteRepository
    from repositories.note_link_repository import NoteLinkRepository
    from services.note_service import NoteService
    from services.note_link_service import NoteLinkService

    note_repo = NoteRepository(db)
    link_repo = NoteLinkRepository(db)
    link_service = NoteLinkService(link_repo, note_repo)
    return NoteService(note_repo, note_link_service=link_service)


# ═══════════════════════════════════════════════════════════════════════════
# Result builder
# ═══════════════════════════════════════════════════════════════════════════

SIDE_EFFECT_ACTIONS = {"create", "update", "delete"}

def _make_result(
    success: bool,
    content: str = "",
    error: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    gathered_context: str = "",
) -> Dict[str, Any]:
    return {
        "result": {
            "success": success,
            "content": content,
            "error": error,
            "metadata": metadata or {},
            "gathered_context": gathered_context,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# Formatting helpers
# ═══════════════════════════════════════════════════════════════════════════

def _format_search_results(data: List[Dict[str, Any]]) -> str:
    if not data:
        return "No matching notes found."
    lines = ["## Retrieved Notes\n"]
    for i, note in enumerate(data, 1):
        score = note.get("score", "")
        score_str = f" (relevance: {score})" if score else ""
        lines.append(f"### Note {i}: {note.get('title', 'Untitled')}{score_str}")
        if note.get("is_important"):
            lines.append("*Important note*")
        col_names = note.get("collection_names", [])
        if col_names:
            lines.append(f"*Collections: {', '.join(col_names)}*")
        content = note.get("content", "")
        if content:
            lines.append(f"\n{content}\n")
        link_count = note.get("outbound_link_count", 0)
        backlink_count = note.get("backlink_count", 0)
        if link_count or backlink_count:
            lines.append(f"*Links: {link_count} outbound, {backlink_count} backlinks*")
        lines.append(f"*Source: {note.get('source', 'user')} | ID: {note.get('id', '')}*\n")
    return "\n".join(lines)


def _format_note_detail(data: Dict[str, Any]) -> str:
    lines = [f"## {data.get('title', 'Untitled')}\n"]
    if data.get("is_important"):
        lines.append("**Important note**\n")
    if data.get("pinned"):
        lines.append("**Pinned**\n")
    col_names = data.get("collection_names", [])
    if col_names:
        lines.append(f"**Collections:** {', '.join(col_names)}\n")
    content = data.get("content", "")
    if content:
        lines.append(content)
        lines.append("")
    todos = data.get("todos", [])
    if todos:
        lines.append("### Checklist")
        for t in todos:
            check = "x" if t.get("done") else " "
            lines.append(f"- [{check}] {t.get('text', '')}")
        lines.append("")
    outbound = data.get("outbound_links", [])
    if outbound:
        lines.append("### Links From This Note")
        for link in outbound:
            target_type = link.get("target_type", "")
            label = link.get("label", "")
            target_title = link.get("target_title", "")
            display = target_title or label or "(unnamed)"
            lines.append(f"- [{target_type}] {display}")
        lines.append("")
    backlinks = data.get("backlinks", [])
    if backlinks:
        lines.append("### Notes Linking Here")
        for bl in backlinks:
            lines.append(f"- {bl.get('title', 'Untitled')} — \"{bl.get('label', '')}\"")
        lines.append("")
    lines.append(
        f"*Source: {data.get('source', 'user')} | "
        f"Created: {data.get('created_at', '')} | "
        f"Updated: {data.get('updated_at', '')} | "
        f"ID: {data.get('id', '')}*"
    )
    return "\n".join(lines)


def _format_collections(data: List[Dict[str, Any]]) -> str:
    if not data:
        return "No collections found."
    lines = ["## Note Collections\n"]
    for col in data:
        lines.append(f"- **{col['name']}** ({col['note_count']} notes) [id: {col['id']}]")
    return "\n".join(lines)


def _format_graph(data: Dict[str, Any]) -> str:
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
        for n in nodes[:30]:
            label = n.get("label", "")
            ntype = n.get("type", "")
            lines.append(f"- [{ntype}] {label}")
    if edges:
        lines.append("\n### Connections")
        for e in edges[:30]:
            src = e.get("source_label", e.get("source", ""))
            tgt = e.get("target_label", e.get("target", ""))
            label = e.get("label", "linked")
            lines.append(f"- {src} → {tgt} ({label})")
    return "\n".join(lines)


def _format_backlinks(data: List[Dict[str, Any]], target_title: str = "") -> str:
    if not data:
        return f"No notes link to {target_title or 'this note'}."
    header = f"## Notes Linking to \"{target_title}\"\n" if target_title else "## Backlinks\n"
    lines = [header]
    for bl in data:
        title = bl.get("title", "Untitled")
        label = bl.get("label", "")
        preview = bl.get("content_preview", "")[:200]
        lines.append(f"### {title}")
        if label:
            lines.append(f"*Link text: \"{label}\"*")
        if preview:
            lines.append(f"{preview}...")
        lines.append(f"*ID: {bl.get('note_id', '')}*\n")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Enrichment helpers
# ═══════════════════════════════════════════════════════════════════════════

def _enrich_with_collection_names(
    results: List[Dict[str, Any]],
    collections_raw: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    col_id_to_name = {c["id"]: c["name"] for c in collections_raw}
    for r in results:
        col_ids = r.get("collection_ids", [])
        r["collection_names"] = [col_id_to_name[cid] for cid in col_ids if cid in col_id_to_name]
    return results


def _enrich_with_link_counts(tool, results: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
    from uuid import UUID
    uid = UUID(user_id)
    for r in results:
        try:
            note_id = UUID(r["id"])
            outbound = tool._link_repo.find_links_by_note(note_id=note_id, user_id=uid)
            backlinks = tool._link_repo.find_backlinks(target_note_id=note_id, user_id=uid)
            r["outbound_link_count"] = len(outbound) if outbound else 0
            r["backlink_count"] = len(backlinks) if backlinks else 0
        except Exception:
            r["outbound_link_count"] = 0
            r["backlink_count"] = 0
    return results


def _resolve_note_id(tool, user_id: str, note_id: Optional[str], note_title: Optional[str]) -> Optional[str]:
    """Resolve a note to its ID via title search if needed."""
    if note_id:
        return note_id
    if not note_title:
        return None
    search_raw = tool.search_notes(query=note_title, user_id=user_id, k=3)
    search_results = json.loads(search_raw) if search_raw else []
    if not search_results:
        return None
    for sr in search_results:
        if note_title.lower() in (sr.get("title", "")).lower():
            return sr["id"]
    return search_results[0]["id"]


# ═══════════════════════════════════════════════════════════════════════════
# Node 1 — load_context (DB only, no LLM)
# ═══════════════════════════════════════════════════════════════════════════

def load_context_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return {"collections_summary": "(no user_id)", "collections_raw": []}

    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        raw = tool.list_collections(user_id)
        collections = json.loads(raw) if raw else []
        log_info(f"Note subgraph: loaded {len(collections)} collection(s)")
    except Exception as exc:
        log_warning(f"Note subgraph: failed to load collections: {exc}")
        return {"collections_summary": "(failed to load)", "collections_raw": []}
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass

    if not collections:
        return {"collections_summary": "(no collections)", "collections_raw": []}

    lines = [f"- [{c['id']}] \"{c['name']}\" ({c['note_count']} notes)" for c in collections]
    return {"collections_summary": "\n".join(lines), "collections_raw": collections}


# ═══════════════════════════════════════════════════════════════════════════
# Node 2 — classify intent (LLM)
# ═══════════════════════════════════════════════════════════════════════════

def classify_node(state: NoteState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    question = state.get("question", "")
    if not question:
        return {"intent": "SEARCH", "intent_data": {"intent": "SEARCH"}}

    prompt = INTENT_PROMPT.format(
        question=question,
        history=(state.get("history") or "(no history)")[:3000],
        context=(state.get("context") or "(none)")[:2000],
        collections_summary=(state.get("collections_summary") or "(none)")[:4000],
    )
    raw = _call_llm(prompt, config=config)
    data = _parse_json_object(raw) or {"intent": "SEARCH"}
    intent = data.get("intent", "SEARCH")
    log_info(f"Note classify: {intent} — {data.get('reasoning', '')}")
    return {"intent": intent, "intent_data": data}


# ═══════════════════════════════════════════════════════════════════════════
# Node 3a — create_node (extract notes from conversation)
# ═══════════════════════════════════════════════════════════════════════════

def create_node(state: NoteState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """Extract notes from conversation and persist them. Side-effect."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot create notes.")

    question = state.get("question", "")
    context = state.get("context", "")

    prompt = NOTE_EXTRACTION_PROMPT.format(
        question=question,
        context=(context or "(no additional context)")[:4000],
    )
    raw = _call_llm(prompt, config=config)
    parsed = _parse_json_array(raw)
    notes = _validate_extracted_notes(parsed)

    if not notes:
        return _make_result(
            success=True,
            content="[]",
            metadata={"action": "create", "note_count": 0},
        )

    # Persist via NoteService
    db = None
    try:
        from infrastructure.database.session import SessionLocal
        db = SessionLocal()
        service = _get_note_service(db)
        from uuid import UUID
        uid = UUID(user_id)
        thread_id = state.get("thread_id")
        created = service.create_notes_from_agent(uid, notes, thread_id=thread_id)
        db.commit()
        log_info(f"Note create: persisted {len(created)} note(s)")
        content = json.dumps(
            [{"id": str(n.id), "title": n.title or "", "content": n.content[:200]} for n in created],
            ensure_ascii=False,
        )
        return _make_result(
            success=True,
            content=content,
            metadata={"action": "create", "note_count": len(created)},
        )
    except Exception as e:
        if db:
            db.rollback()
        log_warning(f"Note create failed: {e}")
        return _make_result(False, error=f"Failed to create notes: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _validate_extracted_notes(parsed: List) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    for item in parsed[:3]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        note: Dict[str, Any] = {"content": content[:500]}
        todos_raw = item.get("todos")
        if isinstance(todos_raw, list) and todos_raw:
            todos = []
            for t in todos_raw[:10]:
                if isinstance(t, dict) and t.get("text"):
                    todos.append({"text": str(t["text"]).strip()[:200], "done": bool(t.get("done", False))})
                elif isinstance(t, str) and t.strip():
                    todos.append({"text": t.strip()[:200], "done": False})
            if todos:
                note["todos"] = todos
        notes.append(note)
    return notes


# ═══════════════════════════════════════════════════════════════════════════
# Node 3b — search_node
# ═══════════════════════════════════════════════════════════════════════════

def search_node(state: NoteState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot search notes.")

    question = state.get("question", "")
    intent_data = state.get("intent_data") or {}
    collections_raw = state.get("collections_raw") or []

    prompt = SEARCH_REFINEMENT_PROMPT.format(
        question=question,
        history=(state.get("history") or "(no history)")[:2000],
        collections_summary=(state.get("collections_summary") or "(none)")[:3000],
    )
    raw = _call_llm(prompt, config=config)
    refined = _parse_json_object(raw) or {}
    search_query = refined.get("query") or intent_data.get("search_query") or question
    collection_id = refined.get("collection_id") or intent_data.get("target_collection_id")

    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        raw_result = tool.search_notes(query=search_query, user_id=user_id, collection_id=collection_id, k=10)
        results = json.loads(raw_result) if raw_result else []
        results = _enrich_with_collection_names(results, collections_raw)
        results = _enrich_with_link_counts(tool, results, user_id)
        formatted = _format_search_results(results)
        return _make_result(
            success=True, content=formatted, gathered_context=formatted,
            metadata={"action": "search", "num_results": len(results), "query": search_query},
        )
    except Exception as e:
        log_warning(f"Note search failed: {e}")
        return _make_result(False, error=f"Note search failed: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3c — get_note_node
# ═══════════════════════════════════════════════════════════════════════════

def get_note_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot retrieve note.")

    intent_data = state.get("intent_data") or {}
    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        note_id = _resolve_note_id(tool, user_id, intent_data.get("target_note_id"), intent_data.get("target_note_title"))
        if not note_id:
            return _make_result(False, error=f"Could not find note matching '{intent_data.get('target_note_title')}'.")

        raw = tool.get_note(user_id, note_id)
        data = json.loads(raw) if raw else {}
        if data.get("error"):
            return _make_result(False, error=data["error"])

        # Enrich with collection names
        collections_raw = state.get("collections_raw") or []
        col_id_to_name = {c["id"]: c["name"] for c in collections_raw}
        data["collection_names"] = [col_id_to_name[cid] for cid in data.get("collection_ids", []) if cid in col_id_to_name]

        # Enrich outbound links with target titles
        for link in data.get("outbound_links", []):
            if link.get("target_note_id"):
                try:
                    target = json.loads(tool.get_note(user_id, link["target_note_id"]) or "{}")
                    link["target_title"] = target.get("title", "")
                except Exception:
                    link["target_title"] = ""

        # Enrich backlinks with source titles
        for bl in data.get("backlinks", []):
            if bl.get("note_id") and not bl.get("title"):
                try:
                    src = json.loads(tool.get_note(user_id, bl["note_id"]) or "{}")
                    bl["title"] = src.get("title", "Untitled")
                except Exception:
                    bl["title"] = "Untitled"

        formatted = _format_note_detail(data)
        return _make_result(success=True, content=formatted, gathered_context=formatted, metadata={"action": "get_note", "note_id": note_id})
    except Exception as e:
        log_warning(f"Note get failed: {e}")
        return _make_result(False, error=f"Failed to retrieve note: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3d — list_collections_node
# ═══════════════════════════════════════════════════════════════════════════

def list_collections_node(state: NoteState) -> Dict[str, Any]:
    collections_raw = state.get("collections_raw") or []
    formatted = _format_collections(collections_raw)
    return _make_result(success=True, content=formatted, gathered_context=formatted, metadata={"action": "list_collections", "count": len(collections_raw)})


# ═══════════════════════════════════════════════════════════════════════════
# Node 3e — collection_notes_node
# ═══════════════════════════════════════════════════════════════════════════

def collection_notes_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot list collection notes.")

    intent_data = state.get("intent_data") or {}
    collection_id = intent_data.get("target_collection_id")
    collection_name = intent_data.get("target_collection_name")
    collections_raw = state.get("collections_raw") or []

    if not collection_id and collection_name:
        name_lower = collection_name.lower()
        for c in collections_raw:
            if name_lower in c["name"].lower() or c["name"].lower() in name_lower:
                collection_id = c["id"]
                collection_name = c["name"]
                break

    if not collection_id:
        return _make_result(False, error=f"Could not find collection matching '{collection_name}'.")

    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        raw = tool.get_collection_notes(user_id, collection_id)
        results = json.loads(raw) if raw else []

        if not results:
            formatted = f"No notes found in collection \"{collection_name or collection_id}\"."
        else:
            lines = [f"## Notes in \"{collection_name or collection_id}\" ({len(results)} notes)\n"]
            for i, note in enumerate(results, 1):
                lines.append(f"### {i}. {note.get('title', 'Untitled')}")
                if note.get("is_important"):
                    lines.append("*Important*")
                content = note.get("content", "")
                if content:
                    lines.append(f"{content[:300]}...")
                lines.append(f"*Source: {note.get('source', 'user')} | ID: {note.get('id', '')}*\n")
            formatted = "\n".join(lines)

        return _make_result(success=True, content=formatted, gathered_context=formatted, metadata={"action": "collection_notes", "collection_id": collection_id, "count": len(results)})
    except Exception as e:
        log_warning(f"Collection notes fetch failed: {e}")
        return _make_result(False, error=f"Failed to get collection notes: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3f — graph_node
# ═══════════════════════════════════════════════════════════════════════════

def graph_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot get note graph.")

    intent_data = state.get("intent_data") or {}
    note_id = intent_data.get("target_note_id")
    note_title = intent_data.get("target_note_title")

    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        if not note_id and note_title:
            note_id = _resolve_note_id(tool, user_id, None, note_title)

        raw = tool.get_note_graph(user_id, note_id=note_id)
        data = json.loads(raw) if raw else {}
        formatted = _format_graph(data)
        return _make_result(
            success=True, content=formatted, gathered_context=formatted,
            metadata={"action": "get_graph", "center_note_id": note_id, "node_count": len(data.get("nodes", [])), "edge_count": len(data.get("edges", []))},
        )
    except Exception as e:
        log_warning(f"Note graph fetch failed: {e}")
        return _make_result(False, error=f"Failed to get note graph: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3g — backlinks_node
# ═══════════════════════════════════════════════════════════════════════════

def backlinks_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot get backlinks.")

    intent_data = state.get("intent_data") or {}
    note_title = intent_data.get("target_note_title", "")

    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        note_id = _resolve_note_id(tool, user_id, intent_data.get("target_note_id"), note_title)
        if not note_id:
            return _make_result(False, error=f"Could not find note matching '{note_title}'.")

        raw = tool.get_backlinks(user_id, note_id)
        data = json.loads(raw) if raw else []
        formatted = _format_backlinks(data, target_title=note_title)
        return _make_result(success=True, content=formatted, gathered_context=formatted, metadata={"action": "get_backlinks", "note_id": note_id, "count": len(data)})
    except Exception as e:
        log_warning(f"Backlinks fetch failed: {e}")
        return _make_result(False, error=f"Failed to get backlinks: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3h — update_node (side-effect)
# ═══════════════════════════════════════════════════════════════════════════

def update_node(state: NoteState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot update note.")

    question = state.get("question", "")
    intent_data = state.get("intent_data") or {}

    # First search for candidate notes so the LLM can pick the right one
    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        title_hint = intent_data.get("target_note_title") or question
        search_raw = tool.search_notes(query=title_hint, user_id=user_id, k=5)
        notes_context = search_raw or "[]"
    except Exception:
        notes_context = "[]"
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass

    prompt = UPDATE_PROMPT.format(
        question=question,
        notes_context=notes_context[:3000],
        collections_summary=(state.get("collections_summary") or "(none)")[:3000],
    )
    raw = _call_llm(prompt, config=config)
    data = _parse_json_object(raw) or {}

    updates = data.get("updates") or {}
    if not updates:
        return _make_result(False, error="No fields to update were specified.")

    ALLOWED_FIELDS = {"title", "content", "todos", "pinned", "is_important", "collection_ids"}
    sanitised = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}
    if not sanitised:
        return _make_result(False, error="No valid updatable fields found.")

    db = None
    try:
        from infrastructure.database.session import SessionLocal
        from uuid import UUID
        db = SessionLocal()
        service = _get_note_service(db)
        uid = UUID(user_id)

        note_id_str = _resolve_note_id_from_data(data, user_id, db)
        if not note_id_str:
            return _make_result(False, error=f"Could not find note matching '{data.get('target_note_title')}'.")

        from schemas.note import NoteUpdate
        update_schema = NoteUpdate(**sanitised)
        result = service.update_note(uid, UUID(note_id_str), update_schema)
        db.commit()

        if not result:
            return _make_result(False, error="Failed to update note.")

        content = json.dumps({"action": "update", "note_id": note_id_str, "updated_fields": list(sanitised.keys())}, ensure_ascii=False)
        return _make_result(success=True, content=content, metadata={"action": "update", "note_id": note_id_str, "updated_fields": list(sanitised.keys())})
    except Exception as e:
        if db:
            db.rollback()
        log_warning(f"Note update failed: {e}")
        return _make_result(False, error=f"Failed to update note: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _resolve_note_id_from_data(data: Dict[str, Any], user_id: str, db) -> Optional[str]:
    note_id = data.get("target_note_id")
    if note_id:
        return note_id
    note_title = data.get("target_note_title")
    if not note_title:
        return None
    from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool
    tool = NoteKnowledgeTool(db)
    return _resolve_note_id(tool, user_id, None, note_title)


# ═══════════════════════════════════════════════════════════════════════════
# Node 3i — delete_node (side-effect)
# ═══════════════════════════════════════════════════════════════════════════

def delete_node(state: NoteState) -> Dict[str, Any]:
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot delete note.")

    intent_data = state.get("intent_data") or {}

    tool = None
    db = None
    try:
        from infrastructure.database.session import SessionLocal
        from uuid import UUID
        db = SessionLocal()
        service = _get_note_service(db)

        # Resolve from knowledge tool first
        from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool
        kt = NoteKnowledgeTool(db)
        note_id = _resolve_note_id(kt, user_id, intent_data.get("target_note_id"), intent_data.get("target_note_title"))
        if not note_id:
            return _make_result(False, error=f"Could not find note matching '{intent_data.get('target_note_title')}'.")

        uid = UUID(user_id)
        deleted = service.delete_note(uid, UUID(note_id))
        db.commit()

        if not deleted:
            return _make_result(False, error="Failed to delete note.")

        content = json.dumps({"action": "delete", "note_id": note_id}, ensure_ascii=False)
        return _make_result(success=True, content=content, metadata={"action": "delete", "note_id": note_id})
    except Exception as e:
        if db:
            db.rollback()
        log_warning(f"Note delete failed: {e}")
        return _make_result(False, error=f"Failed to delete note: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# Node 3j — reason_node (complex multi-step reasoning)
# ═══════════════════════════════════════════════════════════════════════════

def reason_node(state: NoteState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """Multi-step reasoning: LLM plans operations → execute → synthesize."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="No user_id — cannot reason over notes.")

    question = state.get("question", "")

    # Step 1: LLM generates a plan
    plan_prompt = REASON_PLAN_PROMPT.format(
        question=question,
        history=(state.get("history") or "(no history)")[:2000],
        collections_summary=(state.get("collections_summary") or "(none)")[:3000],
    )
    raw_plan = _call_llm(plan_prompt, config=config)
    plan_data = _parse_json_object(raw_plan) or {}
    operations = plan_data.get("plan", [])

    if not operations:
        # Fallback: just do a broad search
        operations = [{"op": "SEARCH", "args": {"query": question}}, {"op": "GET_GRAPH", "args": {}}]

    log_info(f"Note REASON: plan has {len(operations)} operation(s) — {plan_data.get('reasoning', '')}")

    # Step 2: Execute each operation
    tool = None
    db = None
    try:
        tool, db = _get_knowledge_tool()
        collections_raw = state.get("collections_raw") or []
        results_log: List[str] = []

        for i, op in enumerate(operations[:5]):  # hard cap at 5
            op_name = op.get("op", "").upper()
            args = op.get("args", {})
            result_text = _execute_reason_op(tool, op_name, args, user_id, collections_raw)
            results_log.append(f"### Operation {i + 1}: {op_name}\n{result_text}")
            log_info(f"Note REASON op {i + 1}/{len(operations)}: {op_name} → {len(result_text)} chars")

        combined_results = "\n\n".join(results_log)

        # Step 3: LLM synthesizes the final answer
        synth_prompt = REASON_SYNTHESIZE_PROMPT.format(
            question=question,
            results=combined_results[:8000],
        )
        system = (
            "I am the Note Reasoning module. I provide comprehensive, "
            "well-structured answers based on the user's note data. "
            "I use markdown for readability."
        )
        synthesis = _call_llm(synth_prompt, system=system, config=config)

        return _make_result(
            success=True,
            content=synthesis,
            gathered_context=synthesis,
            metadata={"action": "reason", "operations_count": len(operations)},
        )
    except Exception as e:
        log_warning(f"Note reason failed: {e}")
        return _make_result(False, error=f"Complex note reasoning failed: {e}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _execute_reason_op(
    tool,
    op_name: str,
    args: Dict[str, Any],
    user_id: str,
    collections_raw: List[Dict[str, Any]],
) -> str:
    """Execute a single operation within the REASON plan."""
    try:
        if op_name == "SEARCH":
            query = args.get("query", "")
            collection_id = args.get("collection_id")
            raw = tool.search_notes(query=query, user_id=user_id, collection_id=collection_id, k=10)
            results = json.loads(raw) if raw else []
            results = _enrich_with_collection_names(results, collections_raw)
            results = _enrich_with_link_counts(tool, results, user_id)
            return _format_search_results(results)

        elif op_name == "GET_NOTE":
            note_id = args.get("note_id")
            note_title = args.get("note_title")
            resolved = _resolve_note_id(tool, user_id, note_id, note_title)
            if not resolved:
                return f"Note not found: {note_title or note_id}"
            raw = tool.get_note(user_id, resolved)
            data = json.loads(raw) if raw else {}
            col_map = {c["id"]: c["name"] for c in collections_raw}
            data["collection_names"] = [col_map[cid] for cid in data.get("collection_ids", []) if cid in col_map]
            return _format_note_detail(data)

        elif op_name == "LIST_COLLECTIONS":
            return _format_collections(collections_raw)

        elif op_name == "COLLECTION_NOTES":
            col_id = args.get("collection_id")
            col_name = args.get("collection_name")
            if not col_id and col_name:
                for c in collections_raw:
                    if col_name.lower() in c["name"].lower():
                        col_id = c["id"]
                        break
            if not col_id:
                return f"Collection not found: {col_name}"
            raw = tool.get_collection_notes(user_id, col_id)
            results = json.loads(raw) if raw else []
            lines = [f"Collection has {len(results)} notes:"]
            for n in results:
                lines.append(f"- {n.get('title', 'Untitled')} (ID: {n.get('id', '')})")
            return "\n".join(lines)

        elif op_name == "GET_GRAPH":
            note_id = args.get("note_id")
            note_title = args.get("note_title")
            if not note_id and note_title:
                note_id = _resolve_note_id(tool, user_id, None, note_title)
            raw = tool.get_note_graph(user_id, note_id=note_id)
            data = json.loads(raw) if raw else {}
            return _format_graph(data)

        elif op_name == "GET_BACKLINKS":
            note_id = args.get("note_id")
            note_title = args.get("note_title")
            resolved = _resolve_note_id(tool, user_id, note_id, note_title)
            if not resolved:
                return f"Note not found: {note_title or note_id}"
            raw = tool.get_backlinks(user_id, resolved)
            data = json.loads(raw) if raw else []
            return _format_backlinks(data, target_title=note_title or "")

        else:
            return f"Unknown operation: {op_name}"

    except Exception as e:
        return f"Operation {op_name} failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════════════

NODE_LOAD = "load_context"
NODE_CLASSIFY = "classify"
NODE_CREATE = "create"
NODE_SEARCH = "search"
NODE_GET_NOTE = "get_note"
NODE_LIST_COLLECTIONS = "list_collections"
NODE_COLLECTION_NOTES = "collection_notes"
NODE_GRAPH = "get_graph"
NODE_BACKLINKS = "get_backlinks"
NODE_UPDATE = "update"
NODE_DELETE = "delete"
NODE_REASON = "reason"


def _route_after_classify(state: NoteState) -> str:
    intent = state.get("intent", "SEARCH")
    route_map = {
        "CREATE": NODE_CREATE,
        "SEARCH": NODE_SEARCH,
        "GET_NOTE": NODE_GET_NOTE,
        "LIST_COLLECTIONS": NODE_LIST_COLLECTIONS,
        "COLLECTION_NOTES": NODE_COLLECTION_NOTES,
        "GET_GRAPH": NODE_GRAPH,
        "GET_BACKLINKS": NODE_BACKLINKS,
        "UPDATE": NODE_UPDATE,
        "DELETE": NODE_DELETE,
        "REASON": NODE_REASON,
    }
    return route_map.get(intent, NODE_SEARCH)


# ═══════════════════════════════════════════════════════════════════════════
# Build & compile
# ═══════════════════════════════════════════════════════════════════════════

def build_note_subgraph(config: Optional["AgentConfig"] = None) -> StateGraph:
    """
    Build the unified note subgraph.

    Flow:
        START → load_context → classify → [intent handler] → END
    """
    graph = StateGraph(NoteState)

    # ── Nodes ──
    graph.add_node(NODE_LOAD, load_context_node)
    graph.add_node(NODE_CLASSIFY, lambda s: classify_node(s, config=config))
    graph.add_node(NODE_CREATE, lambda s: create_node(s, config=config))
    graph.add_node(NODE_SEARCH, lambda s: search_node(s, config=config))
    graph.add_node(NODE_GET_NOTE, get_note_node)
    graph.add_node(NODE_LIST_COLLECTIONS, list_collections_node)
    graph.add_node(NODE_COLLECTION_NOTES, collection_notes_node)
    graph.add_node(NODE_GRAPH, graph_node)
    graph.add_node(NODE_BACKLINKS, backlinks_node)
    graph.add_node(NODE_UPDATE, lambda s: update_node(s, config=config))
    graph.add_node(NODE_DELETE, delete_node)
    graph.add_node(NODE_REASON, lambda s: reason_node(s, config=config))

    # ── Edges ──
    graph.add_edge(START, NODE_LOAD)
    graph.add_edge(NODE_LOAD, NODE_CLASSIFY)

    all_handlers = [
        NODE_CREATE, NODE_SEARCH, NODE_GET_NOTE, NODE_LIST_COLLECTIONS,
        NODE_COLLECTION_NOTES, NODE_GRAPH, NODE_BACKLINKS,
        NODE_UPDATE, NODE_DELETE, NODE_REASON,
    ]

    graph.add_conditional_edges(
        NODE_CLASSIFY,
        _route_after_classify,
        {n: n for n in all_handlers},
    )

    for handler in all_handlers:
        graph.add_edge(handler, END)

    return graph


# ═══════════════════════════════════════════════════════════════════════════
# Main-graph adapter
# ═══════════════════════════════════════════════════════════════════════════

def create_note_node(config: Optional["AgentConfig"] = None):
    """
    Factory that returns a node function compatible with the main graph.

    The main graph calls:
        graph.add_node(NODE_NOTE, create_note_node(config))

    Behaviour:
        - READ operations (search, get_note, graph, etc.) → append to gathered_context
        - WRITE operations (create, update, delete) → side-effect only, no context append
    """
    subgraph = build_note_subgraph(config=config).compile()

    def note_node(state: Dict[str, Any]) -> Dict[str, Any]:
        log_info("=== Note SubGraph Node ===")

        # ── Adapt main-graph state → NoteState ──
        question = state.get("original_question", "")
        context = state.get("gathered_context", "")
        user_id = state.get("user_id")
        if not user_id:
            meta = state.get("metadata") or {}
            user_id = meta.get("user_id")

        thread_id = state.get("thread_id")
        if not thread_id:
            meta = state.get("metadata") or {}
            thread_id = meta.get("thread_id")

        msgs = list(state.get("messages") or [])
        tail = msgs[-8:] if len(msgs) > 8 else msgs
        history_parts = []
        for m in tail:
            role = getattr(m, "type", "unknown")
            c = str(getattr(m, "content", "") or "")[:500]
            history_parts.append(f"[{role}] {c}")
        history_text = "\n".join(history_parts)

        note_input: NoteState = {
            "question": question,
            "context": context,
            "history": history_text,
            "user_id": str(user_id) if user_id else None,
            "thread_id": str(thread_id) if thread_id else None,
        }

        # ── Run the subgraph ──
        final = subgraph.invoke(note_input)

        # ── Adapt result → main-graph state update ──
        result_data = final.get("result") or {}
        action = (result_data.get("metadata") or {}).get("action", "")

        worker_result = WorkerResult(
            worker_type=WorkerType.NOTE,
            success=result_data.get("success", False),
            content=result_data.get("content", ""),
            error=result_data.get("error"),
            metadata=result_data.get("metadata", {}),
        )

        worker_results = list(state.get("worker_results") or [])
        worker_results.append(worker_result)

        timing = dict(state.get("timing") or {})
        timing["note_ms"] = worker_result.execution_time_ms

        # Side-effect actions (create, update, delete) do NOT add to gathered_context
        gathered = state.get("gathered_context") or ""
        if action not in SIDE_EFFECT_ACTIONS:
            extra_context = result_data.get("gathered_context") or ""
            if not extra_context and worker_result.success and worker_result.content:
                extra_context = worker_result.content
            if extra_context:
                gathered = gathered + f"\n\n=== NOTE ===\n{extra_context}"

        fingerprint = f"note:{action}:{worker_result.success}"
        action_summary = (
            worker_result.content[:120].replace("\n", " ")
            if worker_result.success and worker_result.content
            else (worker_result.error or "no output")[:120]
        )
        completed = list(state.get("completed_actions") or [])
        completed.append({
            "worker": "note",
            "action": action,
            "success": worker_result.success,
            "fingerprint": fingerprint,
            "summary": action_summary,
        })

        return {
            "worker_results": worker_results,
            "gathered_context": gathered,
            "current_worker": None,
            "timing": timing,
            "completed_actions": completed,
        }

    return note_node
