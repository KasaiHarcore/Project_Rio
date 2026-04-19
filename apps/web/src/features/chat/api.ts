import { apiFetch } from '@/shared/api/client'
import type { MessageSource } from '@/features/chat/store'

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
  /** 'user' | 'assistant' | 'tool' */
  role: string;
  content: string;
  created_at: string;
  character_id?: string;
  parent_id?: string | null;
  /** Worker name when role === 'tool' (e.g. 'web', 'rag', 'sql'). */
  tool_name?: string | null;
  metadata?: {
    logic_entries?: Array<{
      title: string;
      detail?: string | null;
      kind: 'thinking' | 'decision' | 'tool-call' | 'info';
    }>;
    sources?: MessageSource[];
  } | null;
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

/**
 * Trigger a regeneration of the assistant response for a given user message.
 * Returns a raw Response so the caller can read the SSE stream.
 */
export async function apiRegenerateMessage(
  threadId: string,
  messageId: string,
  character = 'rio',
): Promise<Response> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  return fetch(`${baseUrl}/api/v1/chat/threads/${threadId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message_id: messageId, character }),
  });
}

/**
 * Edit a previously-sent user message. Creates a new sibling branch:
 * the edited content becomes a new user message (sibling of the original),
 * and the streamed assistant response is its child.
 * Returns a raw Response so the caller can read the SSE stream.
 */
export async function apiEditMessage(
  threadId: string,
  messageId: string,
  newContent: string,
  character = 'rio',
): Promise<Response> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  return fetch(`${baseUrl}/api/v1/chat/threads/${threadId}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      message_id: messageId,
      new_content: newContent,
      character,
    }),
  });
}
