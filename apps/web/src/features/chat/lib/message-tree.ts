/**
 * Message tree builder for conversation branching.
 *
 * Builds a tree from flat messages with parent_id references,
 * and extracts the "active path" for display based on branch selections.
 */

import type { UIMessage } from 'ai'

/* ─── Types ──────────────────────────────────────────────────────── */

export interface MessageNode {
  message: UIMessage
  parentId: string | null
  children: MessageNode[]
  /** 0-based index among siblings with the same parent */
  siblingIndex: number
  /** Total number of siblings (including this node) */
  siblingCount: number
}

/** Map of parentId (or "root") → selected child message ID */
export type BranchSelections = Map<string, string>

/* ─── Build tree ─────────────────────────────────────────────────── */

/**
 * Build a tree of MessageNodes from a flat list of UIMessages.
 *
 * Each message must have `(msg as any).parentId` set (string | null).
 * Messages without a parentId are root nodes.
 *
 * Returns the list of root nodes.
 */
export function buildMessageTree(messages: UIMessage[]): MessageNode[] {
  if (messages.length === 0) return []

  const nodeMap = new Map<string, MessageNode>()

  // First pass: create nodes
  for (const msg of messages) {
    const parentId: string | null = (msg as any).parentId ?? null
    nodeMap.set(msg.id, {
      message: msg,
      parentId,
      children: [],
      siblingIndex: 0,
      siblingCount: 1,
    })
  }

  // Fix orphaned nodes: messages without parent_id that aren't the first
  // message get chained to the previous message in array order.  This
  // handles legacy data (saved before parent_id chaining was added) and
  // mixed threads where only some messages have parent_id set.
  for (let i = 1; i < messages.length; i++) {
    const node = nodeMap.get(messages[i].id)!
    if (node.parentId) continue // already linked
    // Find the closest previous message to use as parent
    const prevId = messages[i - 1].id
    if (nodeMap.has(prevId)) {
      node.parentId = prevId
    }
  }

  // Second pass: link children to parents
  const roots: MessageNode[] = []
  for (const node of nodeMap.values()) {
    if (node.parentId && nodeMap.has(node.parentId)) {
      nodeMap.get(node.parentId)!.children.push(node)
    } else {
      roots.push(node)
    }
  }

  // Third pass: sort children by createdAt and compute sibling indices
  function sortAndIndex(nodes: MessageNode[]) {
    nodes.sort((a, b) => {
      const aTime = ((a.message as any).createdAt as Date)?.getTime() ?? 0
      const bTime = ((b.message as any).createdAt as Date)?.getTime() ?? 0
      return aTime - bTime
    })
    for (let i = 0; i < nodes.length; i++) {
      nodes[i].siblingIndex = i
      nodes[i].siblingCount = nodes.length
    }
  }

  // Apply to roots
  sortAndIndex(roots)

  // Recursively apply to all children
  function walkAndSort(node: MessageNode) {
    if (node.children.length > 0) {
      sortAndIndex(node.children)
      for (const child of node.children) {
        walkAndSort(child)
      }
    }
  }
  for (const root of roots) {
    walkAndSort(root)
  }

  return roots
}

/* ─── Active path extraction ─────────────────────────────────────── */

/**
 * Walk the tree following the selected branch at each fork point.
 * Returns a flat list of messages representing the currently active conversation path.
 *
 * At each fork (node with multiple children), the branch selected in
 * `branchSelections` is followed. If no selection exists, the latest
 * child (last sibling) is used as default.
 */
export function getActivePath(
  roots: MessageNode[],
  branchSelections: BranchSelections,
): UIMessage[] {
  if (roots.length === 0) return []

  const path: UIMessage[] = []

  // Pick the active root
  const selectedRootId = branchSelections.get('root')
  let currentNode = selectedRootId
    ? roots.find((r) => r.message.id === selectedRootId) ?? roots[roots.length - 1]
    : roots[roots.length - 1]

  while (currentNode) {
    path.push(currentNode.message)

    if (currentNode.children.length === 0) break

    const parentId = currentNode.message.id
    const selectedChildId = branchSelections.get(parentId)
    const nextNode = selectedChildId
      ? currentNode.children.find((c) => c.message.id === selectedChildId) ?? currentNode.children[currentNode.children.length - 1]
      : currentNode.children[currentNode.children.length - 1]

    currentNode = nextNode
  }

  return path
}

/* ─── Lookup helpers ─────────────────────────────────────────────── */

/**
 * Find a MessageNode by its message ID in the tree.
 */
export function findNode(roots: MessageNode[], messageId: string): MessageNode | null {
  for (const root of roots) {
    if (root.message.id === messageId) return root
    const found = findNodeRecursive(root, messageId)
    if (found) return found
  }
  return null
}

function findNodeRecursive(node: MessageNode, messageId: string): MessageNode | null {
  for (const child of node.children) {
    if (child.message.id === messageId) return child
    const found = findNodeRecursive(child, messageId)
    if (found) return found
  }
  return null
}

/**
 * Get the siblings of a message (all children of its parent, including itself).
 * Returns null if the message has no siblings (only child or root with no root siblings).
 */
export function getSiblings(roots: MessageNode[], messageId: string): MessageNode[] | null {
  const node = findNode(roots, messageId)
  if (!node) return null

  if (node.siblingCount <= 1) return null

  // Find the parent and return its children
  if (!node.parentId) {
    // It's a root node — siblings are other roots
    return roots.length > 1 ? roots : null
  }

  const parentNode = findNode(roots, node.parentId)
  return parentNode ? parentNode.children : null
}
