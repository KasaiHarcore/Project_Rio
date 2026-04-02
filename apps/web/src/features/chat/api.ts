import { apiFetch } from '@/shared/api/client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ThreadSummary {
  id: string;
  title: string | null;
  status: string;
  is_starred: boolean;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface ThreadPatch {
  title?: string;
  status?: 'active' | 'archived';
  is_starred?: boolean;
  is_pinned?: boolean;
}

export interface MessageRecord {
  id: string;
  role: string;
  content: string;
  created_at: string;
  character_id?: string;
}

export interface MemoryRecord {
  key: string;
  text: string;
  memory_type: string;
  source: string;
  created_at: string;
  mode: string;
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiListThreads(
  limit = 20,
): Promise<{ success: boolean; threads: ThreadSummary[] }> {
  return apiFetch(`/chat/threads?limit=${limit}`);
}

export async function apiGetThreadMessages(
  threadId: string,
  limit = 200,
): Promise<{ success: boolean; messages: MessageRecord[] }> {
  return apiFetch(`/chat/threads/${threadId}/messages?limit=${limit}`);
}

export async function apiDeleteThread(threadId: string): Promise<void> {
  await apiFetch(`/chat/threads/${threadId}`, { method: "DELETE" });
}

export async function apiUpdateThread(
  threadId: string,
  patch: ThreadPatch,
): Promise<ThreadSummary> {
  return apiFetch<ThreadSummary>(`/chat/threads/${threadId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function apiGetThreadMemories(
  threadId: string,
  limit = 50,
): Promise<{ success: boolean; memories: MemoryRecord[]; thread_id: string }> {
  return apiFetch(`/chat/threads/${threadId}/memories?limit=${limit}`);
}
