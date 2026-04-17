/**
 * useMessageExchanges — correlates LogicEntries with message exchanges.
 *
 * Groups user→assistant message pairs into "exchanges", then assigns
 * LogicEntry items to each exchange based on timestamp windows.
 *
 * Tool call branching:
 * - Single tool-call in an exchange → 1 branch node
 * - Multiple parallel tool-calls (within 500ms) → multiple branch nodes
 * - Sequential tool-calls (>500ms apart) → stacked into 1 branch node
 */

import { useMemo } from 'react'
import type { UIMessage } from 'ai'
import type { LogicEntry } from '@/features/chat/store'

/* ─── Types ──────────────────────────────────────────────────────── */

/** A group of sequential tool calls stacked into one visual branch */
export interface ToolBranch {
  id: string
  entries: LogicEntry[]
  /** Whether this branch ran in parallel with other branches */
  parallel: boolean
}

/** A single user→assistant exchange with correlated logic entries */
export interface MessageExchange {
  id: string
  userMessage: UIMessage | null
  assistantMessage: UIMessage | null
  /** All logic entries in this exchange's time window */
  logicEntries: LogicEntry[]
  /** Tool call entries grouped into branches */
  toolBranches: ToolBranch[]
  /** Non-tool logic entries (thinking, decisions, info) */
  thinkingEntries: LogicEntry[]
  timeStart: number
  timeEnd: number
}

/* ─── Helpers ────────────────────────────────────────────────────── */

function getMsgTime(msg: UIMessage): number {
  return ((msg as any).createdAt as Date)?.getTime() ?? 0
}

/** Threshold for considering tool calls "parallel" (ms) */
const PARALLEL_THRESHOLD = 500

/**
 * Group tool-call LogicEntries into branches:
 * - Tools within PARALLEL_THRESHOLD ms of each other → separate parallel branches
 * - Sequential tools beyond threshold → stacked in same branch
 */
function groupToolBranches(toolEntries: LogicEntry[]): ToolBranch[] {
  if (toolEntries.length === 0) return []
  if (toolEntries.length === 1) {
    return [{ id: toolEntries[0].id, entries: toolEntries, parallel: false }]
  }

  // Sort by timestamp
  const sorted = [...toolEntries].sort((a, b) => a.timestamp - b.timestamp)

  const branches: ToolBranch[] = []
  let currentBranch: LogicEntry[] = [sorted[0]]

  for (let i = 1; i < sorted.length; i++) {
    const gap = sorted[i].timestamp - sorted[i - 1].timestamp

    if (gap <= PARALLEL_THRESHOLD) {
      // Within threshold → this is a parallel tool call, start new branch
      // But first, finalize the current branch
      branches.push({
        id: currentBranch[0].id,
        entries: currentBranch,
        parallel: true,
      })
      currentBranch = [sorted[i]]
    } else {
      // Beyond threshold → sequential, stack in same branch
      currentBranch.push(sorted[i])
    }
  }

  // Push the last branch
  if (currentBranch.length > 0) {
    branches.push({
      id: currentBranch[0].id,
      entries: currentBranch,
      parallel: branches.length > 0,
    })
  }

  // If we ended up with only one branch, it's not parallel
  if (branches.length === 1) {
    branches[0].parallel = false
  }

  return branches
}

/* ─── Hook ───────────────────────────────────────────────────────── */

export function useMessageExchanges(
  messages: UIMessage[],
  logicEntries: LogicEntry[],
): MessageExchange[] {
  return useMemo(() => {
    if (messages.length === 0 && logicEntries.length === 0) return []

    // Build exchanges from consecutive user→assistant pairs
    const exchanges: MessageExchange[] = []
    let i = 0

    while (i < messages.length) {
      const msg = messages[i]

      if (msg.role === 'user') {
        const userMsg = msg
        const nextMsg = i + 1 < messages.length ? messages[i + 1] : null
        const assistantMsg = nextMsg?.role === 'assistant' ? nextMsg : null

        exchanges.push({
          id: userMsg.id,
          userMessage: userMsg,
          assistantMessage: assistantMsg,
          logicEntries: [],
          toolBranches: [],
          thinkingEntries: [],
          timeStart: getMsgTime(userMsg),
          timeEnd: 0, // filled below
        })

        i += assistantMsg ? 2 : 1
      } else if (msg.role === 'assistant') {
        // Orphan assistant message (no preceding user msg, e.g. system greeting)
        exchanges.push({
          id: msg.id,
          userMessage: null,
          assistantMessage: msg,
          logicEntries: [],
          toolBranches: [],
          thinkingEntries: [],
          timeStart: getMsgTime(msg),
          timeEnd: 0,
        })
        i += 1
      } else {
        i += 1
      }
    }

    // Fill timeEnd for each exchange
    for (let j = 0; j < exchanges.length; j++) {
      exchanges[j].timeEnd = j + 1 < exchanges.length
        ? exchanges[j + 1].timeStart
        : Infinity
    }

    // Handle pre-conversation logic entries (before first message)
    const firstTime = exchanges.length > 0 ? exchanges[0].timeStart : Infinity

    // Assign logic entries to exchanges by timestamp window
    for (const entry of logicEntries) {
      // Pre-conversation entries
      if (entry.timestamp < firstTime && exchanges.length > 0) {
        exchanges[0].logicEntries.push(entry)
        continue
      }

      for (let j = exchanges.length - 1; j >= 0; j--) {
        if (entry.timestamp >= exchanges[j].timeStart) {
          exchanges[j].logicEntries.push(entry)
          break
        }
      }
    }

    // Within each exchange, separate tool calls from thinking entries and group into branches
    for (const ex of exchanges) {
      const toolEntries = ex.logicEntries.filter((e) => e.kind === 'tool-call')
      const thinkingEntries = ex.logicEntries.filter((e) => e.kind !== 'tool-call')

      ex.toolBranches = groupToolBranches(toolEntries)
      ex.thinkingEntries = thinkingEntries
    }

    return exchanges
  }, [messages, logicEntries])
}
