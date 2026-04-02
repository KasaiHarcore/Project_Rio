"use client"

/**
 * useStreamSidebarReset — Thin hook for sidebar lifecycle.
 *
 * The heavy lifting (parsing the data-stream protocol and dispatching
 * events) is done inside the custom `sidebarFetch` in `chat-transport.ts`.
 *
 * This hook handles **session reset** — clearing the sidebar store
 * when the active thread changes (new chat or switching between existing threads).
 *
 * Usage in MissionControl:
 *   useStreamSidebarReset(isNewChat, threadId)
 */

import { useEffect, useRef } from 'react'
import { useSidebarStore } from '@/features/chat/store'

/**
 * Reset the sidebar store when the active thread changes.
 *
 * @param isNewChat   `true` when the current session is a brand-new chat (no threadId).
 * @param threadId    The current thread ID (undefined/null for new chats).
 */
export function useStreamSidebarReset(isNewChat: boolean, threadId?: string | null) {
  const resetSession = useSidebarStore((s) => s.resetSession)
  const prevThreadIdRef = useRef<string | null | undefined>(threadId)

  useEffect(() => {
    // Reset when starting a new chat OR when switching between existing threads
    if (isNewChat || threadId !== prevThreadIdRef.current) {
      resetSession()
    }
    prevThreadIdRef.current = threadId
  }, [isNewChat, threadId, resetSession])
}
