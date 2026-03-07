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

import { useEffect, useRef } from 'react'
import { useSidebarStore } from '@/store/sidebar-store'
import { setCapturedThreadId } from '@/lib/chat-transport'

/**
 * Reset the sidebar store + captured thread ID when a new chat session starts.
 *
 * @param isNewChat  `true` when the current session is a brand-new chat (no threadId).
 */
export function useStreamSidebarReset(isNewChat: boolean) {
  const resetSession = useSidebarStore((s) => s.resetSession)
  const prevRef = useRef(isNewChat)

  useEffect(() => {
    // Reset when transitioning into a new-chat state, or on first mount if new
    if (isNewChat) {
      resetSession()
      setCapturedThreadId(null)
    }
    prevRef.current = isNewChat
  }, [isNewChat, resetSession])
}
