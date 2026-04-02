import { apiFetch, getAccessToken, ApiError } from '@/shared/api/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface DocumentRecord {
  id: string;
  name: string;
  file_type: string;
  size_bytes: number;
  chunk_count: number;
  status: string;
  error_message: string | null;
  uploaded_at: string;
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiListDocuments(
  limit = 50,
): Promise<{ success: boolean; documents: DocumentRecord[] }> {
  return apiFetch(`/knowledge?limit=${limit}`);
}

export async function apiUploadDocument(
  file: File,
  chunkingStrategy = "recursive",
): Promise<{ success: boolean; document: DocumentRecord; message: string }> {
  const token = getAccessToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(
    `${API_BASE}/api/v1/knowledge/upload?chunking_strategy=${chunkingStrategy}`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    },
  );

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText, body);
  }

  return res.json();
}

export async function apiDeleteDocument(documentId: string): Promise<void> {
  await apiFetch(`/knowledge/${documentId}`, { method: "DELETE" });
}
