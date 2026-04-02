import { apiFetch, getAccessToken, ApiError } from '@/shared/api/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ArtifactRecord {
  id: string;
  user_id: string;
  thread_id: string | null;
  name: string;
  artifact_type: string;
  language: string | null;
  content: string;
  version: number;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiListArtifacts(
  threadId?: string,
  artifactType?: string,
  limit = 50,
): Promise<ArtifactRecord[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (threadId) params.set("thread_id", threadId);
  if (artifactType) params.set("artifact_type", artifactType);
  return apiFetch<ArtifactRecord[]>(`/artifacts?${params}`);
}

export async function apiGetArtifact(id: string): Promise<ArtifactRecord> {
  return apiFetch<ArtifactRecord>(`/artifacts/${id}`);
}

export async function apiCreateArtifact(data: {
  name: string;
  artifact_type?: string;
  language?: string;
  content: string;
  thread_id?: string;
  parent_id?: string;
}): Promise<ArtifactRecord> {
  return apiFetch<ArtifactRecord>("/artifacts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function apiUpdateArtifact(
  id: string,
  data: { name?: string; content?: string; language?: string; artifact_type?: string },
): Promise<ArtifactRecord> {
  return apiFetch<ArtifactRecord>(`/artifacts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function apiDeleteArtifact(id: string): Promise<void> {
  await apiFetch(`/artifacts/${id}`, { method: "DELETE" });
}

export async function apiDownloadArtifact(id: string): Promise<Blob> {
  const token = getAccessToken();
  const res = await fetch(
    `${API_BASE}/api/v1/artifacts/${id}/download`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!res.ok) throw new ApiError(res.status, "Download failed");
  return res.blob();
}
