import { apiFetch, ApiError } from '@/shared/api/client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface NoteRecord {
  id: string;
  title: string;
  content: string;
  thread_id?: string;
  pinned: boolean;
  is_important: boolean;
  source: "agent" | "user";
  collection_ids?: string[];
  todos?: { text: string; done: boolean }[];
  created_at: string;
  updated_at: string;
}

export interface NoteLinkRecord {
  id: string;
  user_id: string;
  note_id: string;
  label: string;
  target_type: "note" | "document" | "artifact" | "media" | "url";
  target_note_id: string | null;
  target_document_id: string | null;
  target_artifact_id: string | null;
  target_url: string | null;
  media_meta: Record<string, unknown> | null;
  position: number | null;
  created_at: string;
  updated_at: string;
}

export interface NoteGraphNode {
  id: string;
  type: string;
  label: string;
  metadata: Record<string, unknown> | null;
}

export interface NoteGraphEdge {
  source_id: string;
  target_id: string;
  label: string;
  target_type: string;
}

export interface NoteGraphStats {
  total_nodes: number;
  total_edges: number;
  total_notes: number;
  total_links: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
}

export interface NoteGraphResponse {
  nodes: NoteGraphNode[];
  edges: NoteGraphEdge[];
  stats: NoteGraphStats;
}

// ── Notes API (uses Next.js proxy) ─────────────────────────────────────────

export async function apiListNotes(
  threadId?: string,
): Promise<NoteRecord[]> {
  const params = new URLSearchParams();
  if (threadId) params.set("thread_id", threadId);
  const qs = params.toString();
  const url = `/api/notes${qs ? `?${qs}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : data.notes ?? [];
}

export async function apiCreateNote(
  note: Partial<NoteRecord>,
): Promise<NoteRecord> {
  const res = await fetch("/api/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(note),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Failed to create note", body);
  }
  return res.json();
}

export async function apiUpdateNote(
  id: string,
  patch: Partial<NoteRecord>,
): Promise<NoteRecord> {
  const res = await fetch(`/api/notes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Failed to update note", body);
  }
  return res.json();
}

export async function apiDeleteNote(id: string): Promise<void> {
  await fetch(`/api/notes/${id}`, { method: "DELETE" });
}

// ── Collections API (uses Next.js proxy) ──────────────────────────────────

export interface CollectionRecord {
  id: string;
  name: string;
  note_count: number;
  created_at: string;
  updated_at: string;
}

export async function apiListCollections(): Promise<CollectionRecord[]> {
  const res = await fetch("/api/collections");
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function apiCreateCollection(
  name: string,
): Promise<CollectionRecord> {
  const res = await fetch("/api/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Failed to create collection", body);
  }
  return res.json();
}

export async function apiUpdateCollection(
  id: string,
  patch: { name?: string },
): Promise<CollectionRecord> {
  const res = await fetch(`/api/collections/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Failed to update collection", body);
  }
  return res.json();
}

export async function apiDeleteCollection(id: string): Promise<void> {
  await fetch(`/api/collections/${id}`, { method: "DELETE" });
}

// ── Note Links API ────────────────────────────────────────────────────────

export async function apiGetNoteGraph(opts?: {
  centerNodeId?: string;
  limit?: number;
}): Promise<NoteGraphResponse> {
  const params = new URLSearchParams();
  if (opts?.centerNodeId) params.set("center_node_id", opts.centerNodeId);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return apiFetch<NoteGraphResponse>(`/note-links/graph${qs ? `?${qs}` : ""}`);
}

export async function apiListNoteLinks(
  noteId?: string,
  targetType?: string,
): Promise<NoteLinkRecord[]> {
  const params = new URLSearchParams();
  if (noteId) params.set("note_id", noteId);
  if (targetType) params.set("target_type", targetType);
  const qs = params.toString();
  return apiFetch<NoteLinkRecord[]>(`/note-links${qs ? `?${qs}` : ""}`);
}

export async function apiGetBacklinks(noteId: string): Promise<NoteLinkRecord[]> {
  return apiFetch<NoteLinkRecord[]>(`/note-links/backlinks/${noteId}`);
}

export async function apiDeleteNoteLink(linkId: string): Promise<void> {
  await apiFetch(`/note-links/${linkId}`, { method: "DELETE" });
}
