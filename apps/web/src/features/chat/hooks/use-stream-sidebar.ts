"use client"

/**
 * useStreamSidebarReset — Thin hook for sidebar lifecycle.
 *
 * The heavy lifting (parsing the data-stream protocol and dispatching
 * events) is done inside the custom `sidebarFetch` in `chat-transport.ts`.
 *
 * This hook only handles **session reset** — clearing the sidebar store
 * when a new chat starts.
 *
 * Usage in MissionControl:
 *   useStreamSidebarReset(isNewChat)
 */

import { useEffect } from 'react'
import { useSidebarStore } from '@/features/chat/store'

/**
 * Reset the sidebar store when a new chat session starts.
 *
 * @param isNewChat  `true` when the current session is a brand-new chat (no threadId).
 */
export function useStreamSidebarReset(isNewChat: boolean) {
  const resetSession = useSidebarStore((s) => s.resetSession)

  useEffect(() => {
    if (isNewChat) {
      resetSession()
    }
  }, [isNewChat, resetSession])
}
