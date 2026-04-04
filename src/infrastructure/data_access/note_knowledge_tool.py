"""Note Knowledge Tool — LLM-agent-facing tool for querying the note system.

Provides structured access to notes, collections, and the note graph.
The agent's supervisor delegates here when it needs to consult the user's notes.

Operations:
    search_notes       — semantic search via Qdrant + graph expansion
    get_note           — full note content + outbound links + backlinks
    list_collections   — all collections with counts
    get_collection_notes — all notes in a collection
    get_note_graph     — local subgraph (1-hop) or full graph
    get_backlinks      — notes that reference a given note
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from utils.log import log_info, log_warning


class NoteKnowledgeTool:
    """Agent-facing tool for querying the note system.

    Requires a DB session to instantiate services. Designed to be
    created per-request in the workflow executor.
    """

    def __init__(self, db_session) -> None:
        from repositories.note_repository import NoteRepository
        from repositories.note_link_repository import NoteLinkRepository
        from services.note_service import NoteService
        from services.note_link_service import NoteLinkService

        note_repo = NoteRepository(db_session)
        link_repo = NoteLinkRepository(db_session)
        self._link_service = NoteLinkService(link_repo, note_repo)
        self._note_service = NoteService(note_repo, note_link_service=self._link_service)
        self._note_repo = note_repo
        self._link_repo = link_repo

    def search_notes(
        self,
        query: str,
        user_id: str,
        collection_id: Optional[str] = None,
        k: int = 10,
    ) -> str:
        """Semantic search across notes with graph-enhanced expansion.

        1. Search Qdrant for top-k semantically similar notes
        2. Expand results by 1-hop graph traversal (linked notes)
        3. Deduplicate and rank by: 0.7 * vector_score + 0.3 * graph_proximity
        4. Fall back to PostgreSQL title/content search if Qdrant unavailable
        """
        uid = UUID(user_id)

        # Try Qdrant vector search first
        vector_hits = []
        try:
            from infrastructure.data_access.note_vector_tool import get_note_vector_tool
            vector_hits = get_note_vector_tool().search(
                query=query,
                user_id=user_id,
                collection_id=collection_id,
                k=k,
            )
        except Exception as e:
            log_warning(f"NoteKnowledgeTool: Qdrant search failed, falling back to DB: {e}")

        if vector_hits:
            # Score map from vector search
            score_map: Dict[str, float] = {}
            for hit in vector_hits:
                score_map[hit["note_id"]] = hit.get("score", 0.0)

            # Graph expansion: 1-hop neighbors of top results
            graph_neighbors: Dict[str, float] = {}
            for hit in vector_hits[:5]:
                try:
                    note_id = UUID(hit["note_id"])
                    # Outbound links
                    outbound = self._link_repo.find_links_by_note(
                        note_id=note_id, user_id=uid
                    )
                    for link in outbound:
                        if link.target_note_id:
                            tid = str(link.target_note_id)
                            if tid not in score_map:
                                graph_neighbors[tid] = max(
                                    graph_neighbors.get(tid, 0.0),
                                    hit.get("score", 0.0) * 0.5,
                                )
                    # Backlinks
                    backlinks = self._link_repo.find_backlinks(
                        target_note_id=note_id, user_id=uid
                    )
                    for link in backlinks:
                        sid = str(link.note_id)
                        if sid not in score_map:
                            graph_neighbors[sid] = max(
                                graph_neighbors.get(sid, 0.0),
                                hit.get("score", 0.0) * 0.4,
                            )
                except Exception:
                    pass

            # Merge: vector hits + graph neighbors
            final_scores: Dict[str, float] = {}
            for nid, vscore in score_map.items():
                gscore = graph_neighbors.get(nid, 0.0)
                final_scores[nid] = 0.7 * vscore + 0.3 * gscore
            for nid, gscore in graph_neighbors.items():
                if nid not in final_scores:
                    final_scores[nid] = 0.3 * gscore

            # Fetch full notes for top results
            sorted_ids = sorted(final_scores, key=lambda x: final_scores[x], reverse=True)[:k]
            results = []
            for nid in sorted_ids:
                note = self._note_service.get_note(uid, UUID(nid))
                if note:
                    results.append({
                        "id": str(note.id),
                        "title": note.title or "",
                        "content": note.content[:1000],
                        "score": round(final_scores[nid], 4),
                        "source": note.source.value,
                        "is_important": note.is_important,
                        "collection_ids": [str(c) for c in (note.collection_ids or [])],
                    })
            return json.dumps(results, ensure_ascii=False)

        # Fallback: PostgreSQL text search
        log_info("NoteKnowledgeTool: using DB fallback search")
        from models.note import Note
        notes = (
            self._note_repo.db.query(Note)
            .filter(
                Note.user_id == uid,
                (Note.title.ilike(f"%{query}%")) | (Note.content.ilike(f"%{query}%"))
            )
            .order_by(Note.updated_at.desc())
            .limit(k)
            .all()
        )
        results = []
        for n in notes:
            col_ids = []
            try:
                col_ids = [str(c) for c in (n.collection_ids or [])]
            except Exception:
                pass
            results.append({
                "id": str(n.id),
                "title": n.title or "",
                "content": n.content[:1000] if n.content else "",
                "score": 1.0,
                "source": n.source.value if n.source else "user",
                "is_important": n.is_important,
                "collection_ids": col_ids,
            })
        return json.dumps(results, ensure_ascii=False)

    def get_note(self, user_id: str, note_id: str) -> str:
        """Get full note content with outbound links and backlinks."""
        uid = UUID(user_id)
        nid = UUID(note_id)

        note = self._note_service.get_note(uid, nid)
        if not note:
            return json.dumps({"error": "Note not found"})

        # Outbound links
        outbound = self._link_service.list_links_by_note(uid, nid)
        outbound_data = [
            {
                "label": l.label,
                "target_type": l.target_type.value,
                "target_note_id": str(l.target_note_id) if l.target_note_id else None,
                "target_url": l.target_url,
            }
            for l in outbound
        ]

        # Backlinks
        backlinks = self._link_service.list_backlinks(uid, nid)
        backlink_data = [
            {"note_id": str(l.note_id), "label": l.label}
            for l in backlinks
        ]

        result = {
            "id": str(note.id),
            "title": note.title or "",
            "content": note.content,
            "source": note.source.value,
            "is_important": note.is_important,
            "pinned": note.pinned,
            "collection_ids": [str(c) for c in note.collection_ids],
            "todos": [t.model_dump() for t in note.todos],
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "outbound_links": outbound_data,
            "backlinks": backlink_data,
        }
        return json.dumps(result, ensure_ascii=False, default=str)

    def list_collections(self, user_id: str) -> str:
        """List all collections with note counts."""
        uid = UUID(user_id)
        from repositories.collection_repository import CollectionRepository
        col_repo = CollectionRepository(self._note_repo.db)
        cols = col_repo.list_by_user(uid)
        counts = col_repo.get_note_counts(uid)

        result = [
            {
                "id": str(c.id),
                "name": c.name,
                "note_count": counts.get(c.id, 0),
            }
            for c in cols
        ]
        return json.dumps(result, ensure_ascii=False)

    def get_collection_notes(self, user_id: str, collection_id: str) -> str:
        """Get all notes in a collection."""
        uid = UUID(user_id)
        cid = UUID(collection_id)
        notes = self._note_service.list_notes(uid, collection_id=cid, limit=200)
        result = [
            {
                "id": str(n.id),
                "title": n.title or "",
                "content": n.content[:500],
                "source": n.source.value,
                "is_important": n.is_important,
            }
            for n in notes
        ]
        return json.dumps(result, ensure_ascii=False)

    def get_note_graph(self, user_id: str, note_id: Optional[str] = None) -> str:
        """Get graph data. If note_id given, return 1-hop subgraph (DB-optimised)."""
        uid = UUID(user_id)

        if note_id:
            nid = UUID(note_id)
            graph = self._link_service.get_note_graph(uid, center_node_id=nid)
        else:
            graph = self._link_service.get_note_graph(uid, limit=200)

        result: dict = {
            "nodes": [{"id": str(n.id), "type": n.type, "label": n.label} for n in graph.nodes],
            "edges": [{"source": str(e.source_id), "target": str(e.target_id), "label": e.label} for e in graph.edges],
            "stats": {
                "total_nodes": graph.stats.total_nodes,
                "total_edges": graph.stats.total_edges,
                "total_notes": graph.stats.total_notes,
                "truncated": graph.stats.truncated,
            },
        }
        if note_id:
            result["center_node"] = note_id
        return json.dumps(result, ensure_ascii=False, default=str)

    def get_backlinks(self, user_id: str, note_id: str) -> str:
        """Get all notes that reference a given note."""
        uid = UUID(user_id)
        nid = UUID(note_id)
        backlinks = self._link_service.list_backlinks(uid, nid)

        result = []
        for link in backlinks:
            note = self._note_service.get_note(uid, link.note_id)
            result.append({
                "note_id": str(link.note_id),
                "title": note.title if note else "",
                "label": link.label,
                "content_preview": note.content[:300] if note else "",
            })
        return json.dumps(result, ensure_ascii=False)
