"""NoteLink service — CRUD and auto-sync for Obsidian-style note links.

Handles manual link creation, content-driven auto-parsing (sync_links_from_content),
backlink retrieval, and graph data generation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from models.note import Note
from models.note_link import NoteLink, NoteLinkTargetType
from repositories.note_link_repository import NoteLinkRepository
from repositories.note_repository import NoteRepository
from schemas.note_link import (
    NoteLinkCreate,
    NoteLinkInDB,
    NoteLinkUpdate,
    NoteGraphEdge,
    NoteGraphNode,
    NoteGraphResponse,
    NoteGraphStats,
)
from utils.link_parser import ParsedLink, extract_links
from utils.log import log_info, log_warning


class NoteLinkService:
    """Service for note link CRUD and auto-sync."""

    def __init__(
        self,
        link_repo: NoteLinkRepository,
        note_repo: NoteRepository,
    ) -> None:
        self._repo = link_repo
        self._note_repo = note_repo


    def get_link(self, user_id: UUID, link_id: UUID) -> Optional[NoteLinkInDB]:
        row = self._repo.find_by_id(link_id=link_id, user_id=user_id)
        return NoteLinkInDB.model_validate(row) if row else None

    def list_links_by_note(
        self,
        user_id: UUID,
        note_id: UUID,
        target_type: Optional[NoteLinkTargetType] = None,
    ) -> List[NoteLinkInDB]:
        rows = self._repo.find_links_by_note(
            note_id=note_id, user_id=user_id, target_type=target_type,
        )
        return [NoteLinkInDB.model_validate(r) for r in rows]

    def list_backlinks(self, user_id: UUID, note_id: UUID) -> List[NoteLinkInDB]:
        rows = self._repo.find_backlinks(target_note_id=note_id, user_id=user_id)
        return [NoteLinkInDB.model_validate(r) for r in rows]

    def list_links(
        self,
        user_id: UUID,
        note_id: Optional[UUID] = None,
        target_type: Optional[NoteLinkTargetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NoteLinkInDB]:
        if note_id:
            return self.list_links_by_note(user_id, note_id, target_type)
        rows = self._repo.find_links_by_user(
            user_id=user_id, target_type=target_type, limit=limit, offset=offset,
        )
        return [NoteLinkInDB.model_validate(r) for r in rows]

    def create_link(self, user_id: UUID, data: NoteLinkCreate) -> NoteLinkInDB:
        link = NoteLink(
            user_id=user_id,
            note_id=data.note_id,
            label=data.label,
            target_type=data.target_type,
            target_note_id=data.target_note_id,
            target_document_id=data.target_document_id,
            target_artifact_id=data.target_artifact_id,
            target_url=data.target_url,
            media_meta=data.media_meta.model_dump() if data.media_meta else None,
            position=data.position,
        )
        self._repo.create(link)
        log_info(f"Created note link {link.id} from note {data.note_id}")
        return NoteLinkInDB.model_validate(link)

    def create_links_bulk(
        self, user_id: UUID, items: List[NoteLinkCreate],
    ) -> List[NoteLinkInDB]:
        links = []
        for data in items:
            links.append(NoteLink(
                user_id=user_id,
                note_id=data.note_id,
                label=data.label,
                target_type=data.target_type,
                target_note_id=data.target_note_id,
                target_document_id=data.target_document_id,
                target_artifact_id=data.target_artifact_id,
                target_url=data.target_url,
                media_meta=data.media_meta.model_dump() if data.media_meta else None,
                position=data.position,
            ))
        self._repo.create_bulk(links)
        log_info(f"Bulk created {len(links)} note links for user {user_id}")
        return [NoteLinkInDB.model_validate(lnk) for lnk in links]

    def update_link(
        self, user_id: UUID, link_id: UUID, data: NoteLinkUpdate,
    ) -> Optional[NoteLinkInDB]:
        link = self._repo.find_by_id(link_id=link_id, user_id=user_id)
        if not link:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "media_meta" and value is not None:
                value = value.model_dump() if hasattr(value, "model_dump") else value
            setattr(link, field, value)

        self._repo.flush()
        return NoteLinkInDB.model_validate(link)

    def delete_link(self, user_id: UUID, link_id: UUID) -> bool:
        return self._repo.delete_by_id(link_id=link_id, user_id=user_id) > 0

    def sync_links_from_content(
        self, user_id: UUID, note_id: UUID, content: str,
    ) -> List[NoteLinkInDB]:
        """Parse note content, diff against existing links, and sync.

        1. Extract links from content via regex parser
        2. Fetch existing NoteLink rows for this note
        3. Diff: create new links, delete removed links
        4. Return the final set of links
        """
        parsed = extract_links(content)
        if not parsed:
            # No links in content — delete all existing
            self._repo.delete_by_note(note_id=note_id, user_id=user_id)
            return []

        existing = self._repo.find_links_by_note(note_id=note_id, user_id=user_id)

        # Build fingerprint sets for diffing
        existing_fps: Dict[Tuple, NoteLink] = {}
        for link in existing:
            fp = self._link_fingerprint(link)
            existing_fps[fp] = link

        parsed_fps: Dict[Tuple, ParsedLink] = {}
        for pl in parsed:
            fp = self._parsed_fingerprint(pl)
            parsed_fps[fp] = pl

        to_delete = set(existing_fps.keys()) - set(parsed_fps.keys())
        for fp in to_delete:
            link = existing_fps[fp]
            self._repo.delete_by_id(link_id=link.id, user_id=user_id)

        to_create = set(parsed_fps.keys()) - set(existing_fps.keys())
        new_links: List[NoteLink] = []
        for fp in to_create:
            pl = parsed_fps[fp]
            link = self._parsed_to_model(user_id, note_id, pl)
            if link:
                new_links.append(link)

        if new_links:
            self._repo.create_bulk(new_links)
            log_info(
                f"Synced links for note {note_id}: "
                f"+{len(new_links)} -{len(to_delete)}"
            )

        final = self._repo.find_links_by_note(note_id=note_id, user_id=user_id)
        return [NoteLinkInDB.model_validate(r) for r in final]

    def get_note_graph(
        self,
        user_id: UUID,
        center_node_id: Optional[UUID] = None,
        limit: int = 500,
    ) -> NoteGraphResponse:
        """Build a graph from note links for visualization.

        Args:
            center_node_id: If provided, return a 1-hop subgraph around this
                note using a targeted DB query (no full-graph load).
            limit: Max nodes to return for the full-graph path. Ignored when
                center_node_id is set.
        """
        if center_node_id:
            links = self._repo.get_subgraph_data(
                user_id=user_id, center_note_id=center_node_id,
            )
        else:
            links = self._repo.get_graph_data_limited(
                user_id=user_id, limit=limit * 2,
            )

        nodes: Dict[UUID, NoteGraphNode] = {}
        edges: List[NoteGraphEdge] = []

        for link in links:
            # Source node (note)
            if link.note_id not in nodes and link.note:
                nodes[link.note_id] = NoteGraphNode(
                    id=link.note_id,
                    type="note",
                    label=link.note.title or "Untitled",
                )

            # Target node
            target_id = self._resolve_target_id(link)
            if target_id and target_id not in nodes:
                nodes[target_id] = NoteGraphNode(
                    id=target_id,
                    type=link.target_type.value,
                    label=self._resolve_target_label(link),
                )

            # Edge
            if target_id:
                edges.append(NoteGraphEdge(
                    source_id=link.note_id,
                    target_id=target_id,
                    label=link.label,
                    target_type=link.target_type,
                ))

        # Truncate to limit (full-graph path only)
        truncated = False
        if not center_node_id and len(nodes) > limit:
            truncated = True
            kept_ids = set(list(nodes.keys())[:limit])
            nodes = {k: v for k, v in nodes.items() if k in kept_ids}
            edges = [
                e for e in edges
                if e.source_id in kept_ids and e.target_id in kept_ids
            ]

        # Get true totals for the full-graph path
        total_links = len(links)
        if not center_node_id and truncated:
            total_links = self._repo.count_by_user(user_id)

        note_count = sum(1 for n in nodes.values() if n.type == "note")
        stats = NoteGraphStats(
            total_nodes=len(nodes) if not truncated else self._repo.count_by_user(user_id),
            total_edges=len(edges),
            total_notes=note_count,
            total_links=total_links,
            returned_nodes=len(nodes),
            returned_edges=len(edges),
            truncated=truncated,
        )

        return NoteGraphResponse(
            nodes=list(nodes.values()),
            edges=edges,
            stats=stats,
        )


    @staticmethod
    def _link_fingerprint(link: NoteLink) -> Tuple:
        """Create a fingerprint for an existing NoteLink for diffing."""
        return (
            link.target_type.value,
            str(link.target_note_id) if link.target_note_id else None,
            str(link.target_document_id) if link.target_document_id else None,
            str(link.target_artifact_id) if link.target_artifact_id else None,
            link.target_url,
            link.label,
        )

    @staticmethod
    def _parsed_fingerprint(pl: ParsedLink) -> Tuple:
        """Create a fingerprint for a ParsedLink for diffing."""
        target_note_id = None
        target_doc_id = None
        target_artifact_id = None

        if pl.target_type == "note" and pl.target_id:
            target_note_id = pl.target_id
        elif pl.target_type == "document" and pl.target_id:
            target_doc_id = pl.target_id
        elif pl.target_type == "artifact" and pl.target_id:
            target_artifact_id = pl.target_id

        return (
            pl.target_type,
            target_note_id,
            target_doc_id,
            target_artifact_id,
            pl.target_url,
            pl.label,
        )

    def _parsed_to_model(
        self, user_id: UUID, note_id: UUID, pl: ParsedLink,
    ) -> Optional[NoteLink]:
        """Convert a ParsedLink to a NoteLink ORM object."""
        target_note_id = None
        target_document_id = None
        target_artifact_id = None

        if pl.target_type == "note" and pl.target_id:
            target_note_id = UUID(pl.target_id)
        elif pl.target_type == "note" and not pl.target_id:
            # Note link by title — try to resolve
            target_note_id = self._resolve_note_by_title(user_id, pl.label)
        elif pl.target_type == "document" and pl.target_id:
            target_document_id = UUID(pl.target_id)
        elif pl.target_type == "artifact" and pl.target_id:
            target_artifact_id = UUID(pl.target_id)

        try:
            target_type = NoteLinkTargetType(pl.target_type)
        except ValueError:
            target_type = NoteLinkTargetType.URL

        return NoteLink(
            user_id=user_id,
            note_id=note_id,
            label=pl.label,
            target_type=target_type,
            target_note_id=target_note_id,
            target_document_id=target_document_id,
            target_artifact_id=target_artifact_id,
            target_url=pl.target_url,
            media_meta=pl.media_meta,
            position=pl.position,
        )

    def _resolve_note_by_title(self, user_id: UUID, title: str) -> Optional[UUID]:
        """Try to find a note by title for [[Note Title]] syntax."""
        from models.note import Note

        note = (
            self._note_repo.db.query(Note)
            .filter(Note.user_id == user_id, Note.title == title)
            .first()
        )
        return note.id if note else None

    @staticmethod
    def _resolve_target_id(link: NoteLink) -> Optional[UUID]:
        """Get the target UUID from a NoteLink (whichever FK is set)."""
        if link.target_note_id:
            return link.target_note_id
        if link.target_document_id:
            return link.target_document_id
        if link.target_artifact_id:
            return link.target_artifact_id
        # For URL/media links, use the link's own ID as the node
        if link.target_url:
            return link.id
        return None

    @staticmethod
    def _resolve_target_label(link: NoteLink) -> str:
        """Get a display label for the target of a NoteLink."""
        if link.target_note and hasattr(link.target_note, "title"):
            return link.target_note.title or "Untitled"
        if link.target_document and hasattr(link.target_document, "name"):
            return link.target_document.name
        if link.target_artifact and hasattr(link.target_artifact, "name"):
            return link.target_artifact.name
        return link.label
