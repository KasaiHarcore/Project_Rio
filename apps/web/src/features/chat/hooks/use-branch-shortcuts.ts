"use client"

import { useEffect } from "react"
import type { UIMessage } from "ai"
import type { MessageNode } from "@/features/chat/lib/message-tree"
import { findNode, getSiblings } from "@/features/chat/lib/message-tree"
import { useBranchStore } from "@/features/chat/stores/branch-store"

/**
 * Keyboard shortcuts for branch navigation:
 *   `[`  → previous sibling on the latest branchable message of the active path
 *   `]`  → next sibling on the latest branchable message of the active path
 *
 * Disabled when an input/textarea/content-editable is focused, or when any
 * meta/ctrl/alt modifier is held.
 *
 * The "latest branchable message" is picked by scanning the active-path messages
 * from newest to oldest and returning the first whose parent has siblings. This
 * matches user intent: pressing `]` cycles variants of the most recent fork.
 */
export function useBranchShortcuts(
  activePathMessages: UIMessage[],
  messageTree: MessageNode[],
): void {
  useEffect(() => {
    if (!messageTree || messageTree.length === 0) return
    if (!activePathMessages || activePathMessages.length === 0) return

    function findLatestBranchable(): {
      parentId: string
      siblings: MessageNode[]
    } | null {
      for (let i = activePathMessages.length - 1; i >= 0; i--) {
        const msg = activePathMessages[i]
        const node = findNode(messageTree, msg.id)
        if (!node || !node.parentId) continue
        const siblings = getSiblings(messageTree, msg.id)
        if (siblings && siblings.length > 1) {
          return { parentId: node.parentId, siblings }
        }
      }
      return null
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "[" && e.key !== "]") return

      const target = e.target instanceof HTMLElement ? e.target : null
      const tag = target?.tagName
      const isEditable =
        tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable ||
        target?.closest(".monaco-editor") != null

      if (isEditable || e.metaKey || e.ctrlKey || e.altKey) return

      const target_ = findLatestBranchable()
      if (!target_) return

      e.preventDefault()
      const { parentId, siblings } = target_
      const store = useBranchStore.getState()
      if (e.key === "[") store.prevBranch(parentId, siblings)
      else store.nextBranch(parentId, siblings)
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [activePathMessages, messageTree])
}
