"use client"

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  type NodeTypes,
  type ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { cn } from '@/shared/lib/utils'
import type { UIMessage } from 'ai'
import {
  User as UserIcon, Bot, Brain, Route, Wrench, Info,
  X, Loader2, ChevronLeft, ChevronRight,
  Database, Globe, Code2, Sparkles,
  Check, Compass, Target,
} from 'lucide-react'
import { useSidebarStore, type LogicEntry, type MessageSource } from '@/features/chat/store'
import { buildMessageTree, getActivePath, getBranchRoot, type MessageNode } from '@/features/chat/lib/message-tree'
import { useBranchStore } from '@/features/chat/stores/branch-store'
import { SourcePreviewCard } from '@/features/chat/components/SourcePreviewCard'
import { deriveMockSources } from '@/features/chat/lib/derive-sources'

/* ─── Types ──────────────────────────────────────────────────────── */

interface ConversationTreeViewProps {
  allMessages: UIMessage[]
  messages: UIMessage[]
  status: 'ready' | 'streaming' | 'submitted' | 'error'
  /** Called when user picks "Branch from here" so the parent can exit tree view. */
  onExitTreeView?: () => void
}

/**
 * EdgeKind — how the edge between a user message and its assistant reply is
 * visually differentiated based on what happened during generation:
 *   - direct   : plain reply, no tools or reasoning events (solid rose)
 *   - thinking : the agent produced planning / reasoning entries (amber dashed)
 *   - tool     : a non-source tool ran (violet dashed)
 *   - source   : a retrieval tool ran (RAG / web / knowledge) — cyan bold
 * Assistant → user edges always use `direct` (it's just the next turn).
 */
type EdgeKind = 'direct' | 'thinking' | 'tool' | 'source'

type MessageNodeData = {
  label: string
  role: 'user' | 'assistant'
  text: string
  time: string
  isActive: boolean
  isSelected: boolean
  logicCount: number
  siblingIndex: number
  siblingCount: number
  isStreaming: boolean
  parentId: string | null
  messageId: string
  /** Tool tags derived from logic_entries in the preceding user→assistant turn */
  toolTags: string[]
  /** Branch-root message ID — nodes on the same branch share this. */
  branchRootId: string
  /** Tailwind-compatible hex color chosen from BRANCH_PALETTE. */
  branchColor: string
  /** True when this node has no children — renders a branch-tip label chip. */
  isLeaf: boolean
  /** True when this branch root IS the trunk (main branch). */
  isTrunk: boolean
  /** Raw text of the branch root message — used as a fallback label. */
  branchRootText: string
  /**
   * When set, this is a synthetic "… N messages …" stand-in for a collapsed
   * linear run. Click to expand.
   */
  collapsed?: {
    /** Stable key for this run — used by expandedRunKeys to track state. */
    key: string
    /** How many real messages are collapsed inside. */
    count: number
    /** First-message preview for the pill label. */
    sampleText: string
  }
}

type MessageFlowNode = Node<MessageNodeData, 'messageNode'>

/* ─── Constants ──────────────────────────────────────────────────── */

const NODE_WIDTH = 240
const NODE_HEIGHT = 90
const LOGIC_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  thinking: Brain, decision: Route, 'tool-call': Wrench, info: Info,
}
const LOGIC_COLORS: Record<string, string> = {
  thinking: 'text-rose-400', decision: 'text-emerald-400',
  'tool-call': 'text-violet-400', info: 'text-sky-400',
}

/** Worker names that represent retrieval sources (RAG / web search / KB). */
const SOURCE_WORKERS = new Set(['rag', 'web', 'search', 'knowledge', 'kb', 'retrieval'])

/**
 * Branch color palette — each branch in the tree gets one of these colors
 * assigned by hashing its branch-root message id. Chosen for dark-mode
 * contrast against the `#0c1524` canvas background, following the 8-color
 * cycling convention used by GitLens / Git Graph / JetBrains.
 *
 * The active path always wins: its edges stay rose (per EDGE_STYLES). Branch
 * color tints the NON-active sibling branches so users can tell them apart
 * at a glance.
 */
const BRANCH_PALETTE = [
  '#22d3ee', // cyan
  '#f59e0b', // amber
  '#a78bfa', // violet
  '#10b981', // emerald
  '#fb7185', // rose-lite
  '#fb923c', // orange
  '#2dd4bf', // teal
  '#f472b6', // pink
] as const

function hashStringToIndex(s: string, modulo: number): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0
  }
  return Math.abs(h) % modulo
}

/** Return a stable hex color for a branch-root message id. */
function branchColorFor(branchRootId: string): string {
  return BRANCH_PALETTE[hashStringToIndex(branchRootId, BRANCH_PALETTE.length)]
}

/** Trunk color — the main branch (whichever branch root anchors the tree root) stays rose. */
const TRUNK_COLOR = '#f43f5e'

const EDGE_STYLES: Record<EdgeKind, {
  stroke: string
  strokeWidth: number
  dasharray?: string
}> = {
  direct:   { stroke: '#f43f5e', strokeWidth: 2 },                    // rose — normal reply
  thinking: { stroke: '#f59e0b', strokeWidth: 2, dasharray: '5 3' },  // amber dashed — reasoning
  tool:     { stroke: '#a78bfa', strokeWidth: 2, dasharray: '7 2' },  // violet long-dashed — tool call
  source:   { stroke: '#22d3ee', strokeWidth: 2.5 },                  // cyan bold — retrieval
}

/** Icon + color per tool tag chip. */
const TOOL_CHIP_META: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; label: string }> = {
  rag:        { icon: Database, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',   label: 'RAG' },
  knowledge:  { icon: Database, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',   label: 'KB' },
  kb:         { icon: Database, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',   label: 'KB' },
  retrieval:  { icon: Database, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',   label: 'DOC' },
  web:        { icon: Globe,    color: 'bg-sky-500/20 text-sky-300 border-sky-500/30',      label: 'WEB' },
  search:     { icon: Globe,    color: 'bg-sky-500/20 text-sky-300 border-sky-500/30',      label: 'WEB' },
  sql:        { icon: Code2,    color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', label: 'SQL' },
}

const DEFAULT_TOOL_CHIP = {
  icon: Sparkles,
  color: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  label: '',
}

/* ─── Helpers ────────────────────────────────────────────────────── */

function truncate(text: string, max: number): string {
  if (!text) return ''
  const clean = text.replace(/\n/g, ' ').trim()
  return clean.length > max ? clean.slice(0, max) + '...' : clean
}

function getMsgText(msg: UIMessage): string {
  return msg.parts
    ?.filter((p: any) => p.type === 'text')
    .map((p: any) => p.text)
    .join('') || (msg as any).content || ''
}

function getMsgTime(msg: UIMessage): string {
  const d = (msg as any).createdAt as Date | undefined
  if (!d || isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getLogicForMessage(
  msg: UIMessage, nextMsg: UIMessage | null, logicEntries: LogicEntry[],
): LogicEntry[] {
  const msgTime = ((msg as any).createdAt as Date)?.getTime() ?? 0
  const nextTime = nextMsg
    ? ((nextMsg as any).createdAt as Date)?.getTime() ?? Infinity
    : Infinity
  return logicEntries.filter((e) => e.timestamp >= msgTime && e.timestamp < nextTime)
}

/**
 * Extract a worker name from a tool-call entry title. The transport emits
 * titles like "rag completed", "web failed", "sql completed" — we take the
 * first word and lowercase it.
 */
function extractWorker(title: string): string | null {
  const match = title.match(/^([A-Za-z][\w-]*)\s+(completed|failed|started|running)?/)
  return match ? match[1].toLowerCase() : null
}

/**
 * Classify a user→assistant edge based on logic_entries that fall in the
 * turn's time window. Also returns the distinct tool tags to render as
 * chips on the assistant node.
 */
function classifyEdge(
  parentMsg: UIMessage,
  childMsg: UIMessage,
  logicEntries: LogicEntry[],
): { kind: EdgeKind; tools: string[] } {
  const startTime = ((parentMsg as any).createdAt as Date)?.getTime() ?? 0
  const endTime = ((childMsg as any).createdAt as Date)?.getTime() ?? Infinity
  const inWindow = logicEntries.filter((e) => e.timestamp >= startTime && e.timestamp <= endTime)

  const tools = new Set<string>()
  let hasThinking = false
  let hasSource = false
  let hasTool = false

  for (const e of inWindow) {
    if (e.kind === 'tool-call') {
      hasTool = true
      const worker = extractWorker(e.title)
      if (worker) {
        tools.add(worker)
        if (SOURCE_WORKERS.has(worker)) hasSource = true
      }
    } else if (e.kind === 'thinking') {
      hasThinking = true
    }
  }

  if (hasSource) return { kind: 'source', tools: Array.from(tools) }
  if (hasTool) return { kind: 'tool', tools: Array.from(tools) }
  if (hasThinking) return { kind: 'thinking', tools: [] }
  return { kind: 'direct', tools: [] }
}

/* ─── Lane-based layout (git log --graph style) ─────────────────── */
// Replaces dagre. Each branch gets its own vertical column ("lane") so
// sibling branches never cross. The "preferred" child at each fork — the
// one on the active path — keeps the parent's lane; others get new
// lanes to the right. Lanes are reclaimed after a subtree finishes so
// the graph stays narrow.

const LANE_WIDTH = 280   // horizontal distance between lanes
const ROW_HEIGHT = 120   // vertical distance between depth rows

interface LanePosition { lane: number; depth: number }

function assignLanes(
  roots: MessageNode[],
  activePathIds: Set<string>,
): Map<string, LanePosition> {
  const positions = new Map<string, LanePosition>()
  const occupiedLanes = new Set<number>()

  const nextFreeLane = (): number => {
    for (let i = 0; i < 1000; i++) {
      if (!occupiedLanes.has(i)) return i
    }
    return occupiedLanes.size
  }

  const walk = (node: MessageNode, lane: number, depth: number): void => {
    positions.set(node.message.id, { lane, depth })
    if (node.children.length === 0) return
    // Preferred child first: the one on the active path (if any), else the
    // last sibling (latest by createdAt — matches getActivePath's default).
    const children = [...node.children]
    const activeIdx = children.findIndex((c) => activePathIds.has(c.message.id))
    let preferred: MessageNode
    let others: MessageNode[]
    if (activeIdx >= 0) {
      preferred = children[activeIdx]
      others = children.filter((_, i) => i !== activeIdx)
    } else {
      preferred = children[children.length - 1]
      others = children.slice(0, -1)
    }
    // Preferred child keeps parent's lane — the trunk stays straight.
    walk(preferred, lane, depth + 1)
    // Other siblings each get their own lane, released after their subtree.
    for (const child of others) {
      const newLane = nextFreeLane()
      occupiedLanes.add(newLane)
      walk(child, newLane, depth + 1)
      occupiedLanes.delete(newLane)
    }
  }

  roots.forEach((root, rootIdx) => {
    let laneForRoot: number
    if (rootIdx === 0) {
      laneForRoot = 0
      occupiedLanes.add(0)
    } else {
      laneForRoot = nextFreeLane()
      occupiedLanes.add(laneForRoot)
    }
    walk(root, laneForRoot, 0)
    occupiedLanes.delete(laneForRoot)
  })

  return positions
}

function applyLaneLayout(
  nodes: MessageFlowNode[],
  roots: MessageNode[],
  activePathIds: Set<string>,
): MessageFlowNode[] {
  const positions = assignLanes(roots, activePathIds)
  // Collapsed synthetic nodes use the position of their run-start.
  return nodes.map((node) => {
    const id = node.id
    const key = id.startsWith('collapsed:') ? id.slice('collapsed:'.length).split(':')[0] : id
    const pos = positions.get(key) ?? { lane: 0, depth: 0 }
    return {
      ...node,
      position: {
        x: pos.lane * LANE_WIDTH,
        y: pos.depth * ROW_HEIGHT,
      },
    }
  })
}

// Legacy dagre helper kept for reference but no longer called; marked
// unused so the linter prunes if it wants. Remove in a follow-up.
function layoutWithDagre(nodes: MessageFlowNode[], edges: Edge[]): MessageFlowNode[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 60 })

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  return nodes.map((node) => {
    const pos = g.node(node.id)
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    }
  })
}

/* ─── Tree → React Flow conversion ──────────────────────────────── */

/** Minimum consecutive single-sibling single-child nodes that trigger collapse. */
const COMPACT_MIN_RUN = 4

function treeToFlow(
  roots: MessageNode[],
  activePathIds: Set<string>,
  selectedNodeId: string | null,
  logicEntries: LogicEntry[],
  allMessages: UIMessage[],
  isStreaming: boolean,
  compactMode: boolean,
  expandedRunKeys: Set<string>,
): { nodes: MessageFlowNode[]; edges: Edge[] } {
  const nodes: MessageFlowNode[] = []
  const edges: Edge[] = []

  // Build a parent lookup so we can classify the edge that LEADS to each node
  // and thereby derive tool tags for assistant nodes.
  const parentById = new Map<string, MessageNode>()
  function indexParents(node: MessageNode) {
    for (const child of node.children) {
      parentById.set(child.message.id, node)
      indexParents(child)
    }
  }
  for (const root of roots) indexParents(root)

  // ── Compact mode: identify collapsible linear runs ──
  // A run is a chain of nodes where each has siblingCount === 1 and ≤ 1
  // children. Runs with ≥ COMPACT_MIN_RUN length and whose key is not in
  // expandedRunKeys render as a single synthetic "… N messages …" node.
  type RunInfo = { key: string; run: MessageNode[]; index: number }
  const runByNodeId = new Map<string, RunInfo>()
  if (compactMode) {
    const seenStart = new Set<string>()
    const tryStartRun = (node: MessageNode) => {
      if (seenStart.has(node.message.id)) return
      const parent = parentById.get(node.message.id)
      const parentIsCollapsible =
        parent && parent.siblingCount === 1 && parent.children.length <= 1
      if (parentIsCollapsible) return  // not the start
      // Walk down the chain
      const run: MessageNode[] = []
      let cur: MessageNode | null = node
      while (cur && cur.siblingCount === 1 && cur.children.length <= 1) {
        run.push(cur)
        seenStart.add(cur.message.id)
        cur = cur.children[0] ?? null
      }
      if (run.length >= COMPACT_MIN_RUN) {
        const key = `run:${run[0].message.id}:${run[run.length - 1].message.id}`
        run.forEach((n, i) => runByNodeId.set(n.message.id, { key, run, index: i }))
      }
    }
    function scanForRuns(node: MessageNode) {
      tryStartRun(node)
      for (const child of node.children) scanForRuns(child)
    }
    for (const root of roots) scanForRuns(root)
  }

  /** Does `nodeId` belong to a collapse run that's not currently expanded? */
  function inCollapsedRun(nodeId: string): RunInfo | null {
    const info = runByNodeId.get(nodeId)
    if (!info) return null
    if (expandedRunKeys.has(info.key)) return null
    return info
  }

  /** When an edge would point at a collapsed node, re-target it to the synthetic. */
  function collapsedTargetId(nodeId: string): string {
    const info = inCollapsedRun(nodeId)
    return info ? `collapsed:${info.key}` : nodeId
  }

  // Pre-compute branch root for every node by walking parents. Trunk branches
  // (i.e. paths descending from the tree root with no fork above them) get a
  // special color; other branches pick from BRANCH_PALETTE via hash.
  const branchRootById = new Map<string, string>()
  const computeBranchRoot = (start: MessageNode): string => {
    let current: MessageNode | null = start
    while (current) {
      if (current.siblingCount > 1) return current.message.id
      const parent: MessageNode | null = parentById.get(current.message.id) ?? null
      if (!parent) return current.message.id
      current = parent
    }
    return start.message.id
  }
  function indexBranchRoots(node: MessageNode) {
    branchRootById.set(node.message.id, computeBranchRoot(node))
    for (const child of node.children) indexBranchRoots(child)
  }
  for (const root of roots) indexBranchRoots(root)

  // Trunk = branch root of the first tree root. All nodes with that branchRootId
  // are on the trunk and keep the rose color as their branch color.
  const trunkRootId = roots.length > 0 ? branchRootById.get(roots[0].message.id) : null

  const colorForBranch = (branchRootId: string): string => {
    if (branchRootId === trunkRootId) return TRUNK_COLOR
    return branchColorFor(branchRootId)
  }

  /** Nodes already emitted, to avoid duplicating synthetic collapsed nodes. */
  const emittedNodeIds = new Set<string>()

  function walk(node: MessageNode) {
    const msg = node.message

    // Compact-mode handling: if this node is inside a collapsed run...
    const runInfo = inCollapsedRun(msg.id)
    if (runInfo) {
      if (runInfo.index === 0) {
        // Emit ONE synthetic node representing the whole run, then walk the
        // children of the last node in the run so traversal continues past it.
        const syntheticId = `collapsed:${runInfo.key}`
        if (!emittedNodeIds.has(syntheticId)) {
          emittedNodeIds.add(syntheticId)

          const firstMsg = runInfo.run[0].message
          const lastNode = runInfo.run[runInfo.run.length - 1]
          const lastMsg = lastNode.message
          const runFullyActive = runInfo.run.every((n) => activePathIds.has(n.message.id))

          const firstBranchRootId = branchRootById.get(firstMsg.id) ?? firstMsg.id
          const firstBranchColor = colorForBranch(firstBranchRootId)
          const firstBranchRootMsg = allMessages.find((m) => m.id === firstBranchRootId)
          const firstBranchRootText = firstBranchRootMsg ? getMsgText(firstBranchRootMsg) : ''

          nodes.push({
            id: syntheticId,
            type: 'messageNode',
            position: { x: 0, y: 0 },
            data: {
              label: `${runInfo.run.length} messages`,
              role: 'assistant',
              text: '',
              time: '',
              isActive: runFullyActive,
              isSelected: false,
              logicCount: 0,
              siblingIndex: 0,
              siblingCount: 1,
              isStreaming: false,
              parentId: runInfo.run[0].parentId,
              messageId: syntheticId,
              toolTags: [],
              branchRootId: firstBranchRootId,
              branchColor: firstBranchColor,
              isLeaf: lastNode.children.length === 0,
              isTrunk: firstBranchRootId === trunkRootId,
              branchRootText: firstBranchRootText,
              collapsed: {
                key: runInfo.key,
                count: runInfo.run.length,
                sampleText: getMsgText(firstMsg),
              },
            },
          })

          // Walk children of the LAST in-run node so the tree continues past
          // the collapsed segment. Each child edge is sourced from the
          // synthetic node, not from the real last-in-run node.
          for (const child of lastNode.children) {
            const isActiveEdge =
              activePathIds.has(lastMsg.id) && activePathIds.has(child.message.id)
            const childBranchRootId = branchRootById.get(child.message.id) ?? child.message.id
            const childBranchColor = colorForBranch(childBranchRootId)
            const targetId = collapsedTargetId(child.message.id)

            edges.push({
              id: `e-${syntheticId}-${targetId}`,
              source: syntheticId,
              target: targetId,
              type: 'step',
              animated: isActiveEdge,
              style: {
                stroke: isActiveEdge ? TRUNK_COLOR : childBranchColor,
                strokeWidth: 2,
                opacity: isActiveEdge ? 1 : 0.35,
              },
              data: { kind: 'direct' as EdgeKind, branchRootId: childBranchRootId },
            })
            walk(child)
          }
        }
      }
      // Mid-run nodes are represented by the synthetic — skip emission.
      return
    }

    const msgIdx = allMessages.findIndex((m) => m.id === msg.id)
    const nextMsg = msgIdx >= 0 && msgIdx + 1 < allMessages.length ? allMessages[msgIdx + 1] : null
    const relatedLogic = getLogicForMessage(msg, nextMsg, logicEntries)

    // Tool tags on THIS node come from classifying its incoming edge
    // (parent-user → this-assistant). User nodes never carry tool tags.
    let toolTags: string[] = []
    if (msg.role === 'assistant') {
      const parent = parentById.get(msg.id)
      if (parent && parent.message.role === 'user') {
        toolTags = classifyEdge(parent.message, msg, logicEntries).tools
      }
    }

    const branchRootId = branchRootById.get(msg.id) ?? msg.id
    const branchColor = colorForBranch(branchRootId)
    const isTrunk = branchRootId === trunkRootId
    const branchRootMsg = allMessages.find((m) => m.id === branchRootId)
    const branchRootText = branchRootMsg ? getMsgText(branchRootMsg) : ''

    emittedNodeIds.add(msg.id)
    nodes.push({
      id: msg.id,
      type: 'messageNode',
      position: { x: 0, y: 0 },
      data: {
        label: getMsgText(msg),
        role: msg.role as 'user' | 'assistant',
        text: getMsgText(msg),
        time: getMsgTime(msg),
        isActive: activePathIds.has(msg.id),
        isSelected: selectedNodeId === msg.id,
        logicCount: relatedLogic.length,
        siblingIndex: node.siblingIndex,
        siblingCount: node.siblingCount,
        isStreaming: isStreaming && node.children.length === 0 && msg.role === 'assistant',
        parentId: node.parentId,
        messageId: msg.id,
        toolTags,
        branchRootId,
        branchColor,
        isLeaf: node.children.length === 0,
        isTrunk,
        branchRootText,
      },
    })

    for (const child of node.children) {
      const isActiveBranch = activePathIds.has(msg.id) && activePathIds.has(child.message.id)

      // Only user→assistant turns carry a meaningful "edge kind". Other edges
      // (assistant→user follow-up) are always `direct`.
      const isUserToAssistant = msg.role === 'user' && child.message.role === 'assistant'
      const kind: EdgeKind = isUserToAssistant
        ? classifyEdge(msg, child.message, logicEntries).kind
        : 'direct'
      const base = EDGE_STYLES[kind]

      // Edge stroke: on the active path OR for retrieval edges, keep the
      // kind-specific color (source = cyan, thinking = amber, etc). For
      // inactive `direct` edges, tint toward the child's branch color so
      // sibling branches read as visually distinct lanes.
      const childBranchRootId = branchRootById.get(child.message.id) ?? child.message.id
      const childBranchColor = colorForBranch(childBranchRootId)
      const strokeColor = isActiveBranch
        ? base.stroke
        : kind === 'direct'
          ? childBranchColor
          : base.stroke

      // If the child starts a collapsed run, re-target the edge to the
      // synthetic node so we don't create a dangling edge to a hidden node.
      const targetId = collapsedTargetId(child.message.id)

      edges.push({
        id: `e-${msg.id}-${targetId}`,
        source: msg.id,
        target: targetId,
        type: 'step',
        animated: isActiveBranch && kind !== 'direct',
        style: {
          stroke: strokeColor,
          strokeWidth: isActiveBranch ? base.strokeWidth + 0.5 : base.strokeWidth,
          strokeDasharray: base.dasharray,
          opacity: isActiveBranch ? 1 : 0.35,
        },
        data: { kind, branchRootId: childBranchRootId },
      })
      walk(child)
    }
  }

  for (const root of roots) {
    walk(root)
  }

  return { nodes, edges }
}

/* ─── Custom Node Component ──────────────────────────────────────── */

function MessageNodeComponent({ data }: NodeProps<MessageFlowNode>) {
  const d = data as unknown as MessageNodeData
  const isAssistant = d.role === 'assistant'

  // Collapsed-run variant — renders a single "… N messages …" pill in place
  // of a straight chain of single-child messages. Click to expand.
  if (d.collapsed) {
    const handleExpand = (e: React.MouseEvent) => {
      e.stopPropagation()
      window.dispatchEvent(new CustomEvent('rio:expand-run', {
        detail: { key: d.collapsed!.key },
      }))
    }
    return (
      <>
        <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
        <button
          onClick={handleExpand}
          className={cn(
            "nodrag w-[240px] rounded-lg border-2 border-dashed px-3 py-2.5 text-left transition-all cursor-pointer",
            "flex items-center gap-2",
            d.isActive
              ? "border-slate-600 bg-[#1a1520]/80 hover:bg-[#1a1520]"
              : "border-slate-800 bg-[#0c1524]/60 opacity-50 hover:opacity-90",
          )}
          title={`Click to expand ${d.collapsed.count} messages`}
        >
          <div className="flex-shrink-0 flex flex-col items-center gap-0.5">
            <div className="w-1 h-1 rounded-full bg-slate-500" />
            <div className="w-1 h-1 rounded-full bg-slate-500" />
            <div className="w-1 h-1 rounded-full bg-slate-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[9px] font-black uppercase tracking-[0.15em] text-slate-400">
              {d.collapsed.count} messages
            </p>
            <p className="text-[10px] text-slate-500 truncate italic">
              {truncate(d.collapsed.sampleText, 48)}
            </p>
          </div>
          <span className="text-[8px] font-bold uppercase tracking-wider text-slate-500">
            Expand
          </span>
        </button>
        <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
      </>
    )
  }

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation()
    // Dispatch a custom event that the tree view listens for; this keeps node
    // code free of tree-wide state.
    window.dispatchEvent(new CustomEvent('rio:branch-nav', {
      detail: { direction: 'prev', messageId: d.messageId, parentId: d.parentId },
    }))
  }

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation()
    window.dispatchEvent(new CustomEvent('rio:branch-nav', {
      detail: { direction: 'next', messageId: d.messageId, parentId: d.parentId },
    }))
  }

  // Role-specific styling so user vs assistant is distinguishable at a glance.
  const roleIconBg = isAssistant ? 'bg-rose-500/20' : 'bg-sky-500/20'
  const roleIconColor = isAssistant ? 'text-rose-400' : 'text-sky-400'
  const roleLabelColor = isAssistant ? 'text-rose-400' : 'text-sky-400'
  const accentBorder = d.isActive
    ? isAssistant ? 'border-rose-500/80' : 'border-sky-500/80'
    : isAssistant ? 'border-rose-900/30' : 'border-sky-900/30'

  // Branch lane indicator: a 3px vertical strip along the left edge of the
  // card, tinted with the branch color. This gives every branch a visible
  // "lane" identity (GitLens / Git Graph convention) without overwriting the
  // role-based accents used elsewhere.
  const showLaneMarker = d.branchColor !== TRUNK_COLOR

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
      <div
        data-active={d.isActive ? '1' : '0'}
        className={cn(
          "relative w-[240px] rounded-lg border-2 px-3 py-2.5 transition-all cursor-pointer overflow-hidden",
          d.isSelected
            ? "ring-2 ring-rose-500 border-rose-500 bg-[#1a1520] shadow-[0_0_20px_rgba(244,63,94,0.55)]"
            : d.isActive
              ? cn(accentBorder, "bg-[#1a1520]/95 shadow-[0_0_12px_rgba(244,63,94,0.35)]")
              : cn(accentBorder, "bg-[#1a1520]/40 opacity-35 hover:opacity-80"),
        )}
      >
        {/* Branch lane marker — left-edge stripe in the branch color */}
        {showLaneMarker && (
          <div
            aria-hidden
            className="absolute top-0 left-0 bottom-0 w-[3px]"
            style={{ backgroundColor: d.branchColor, opacity: d.isActive ? 0.95 : 0.6 }}
          />
        )}

        {/* Role header */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <div className={cn(
            "w-4 h-4 rounded flex items-center justify-center flex-shrink-0",
            roleIconBg,
          )}>
            {isAssistant
              ? <Bot className={cn("h-2.5 w-2.5", roleIconColor)} />
              : <UserIcon className={cn("h-2.5 w-2.5", roleIconColor)} />
            }
          </div>
          <span className={cn("text-[9px] font-bold tracking-wider", roleLabelColor)}>
            {isAssistant ? 'Assistant' : 'User'}
          </span>
          {/* Branch color dot — tiny indicator next to the role label so users
              can associate the card with its edge / lane color at a glance. */}
          {showLaneMarker && (
            <span
              aria-hidden
              className="inline-block w-1.5 h-1.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: d.branchColor, opacity: d.isActive ? 1 : 0.7 }}
              title="Branch color"
            />
          )}
          {d.time && (
            <span className="text-[8px] text-slate-500 font-mono ml-auto">[{d.time}]</span>
          )}
          {d.isActive && (
            <div className="w-1.5 h-1.5 rounded-full bg-rose-400 ml-1 flex-shrink-0 animate-pulse" />
          )}
        </div>

        {/* Message content */}
        <p className="text-[10px] text-slate-300 leading-snug line-clamp-2">
          {d.isStreaming ? (
            <span className="flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin text-rose-400" />
              <span className="text-rose-400/70">Generating...</span>
            </span>
          ) : (
            truncate(d.text, 80)
          )}
        </p>

        {/* Source / tool chips — what the assistant used to produce this reply */}
        {d.toolTags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {d.toolTags.map((tag) => {
              const meta = TOOL_CHIP_META[tag] ?? {
                ...DEFAULT_TOOL_CHIP,
                label: tag.toUpperCase().slice(0, 6),
              }
              const Icon = meta.icon
              return (
                <span
                  key={tag}
                  className={cn(
                    "inline-flex items-center gap-0.5 px-1 py-[1px] rounded border text-[7px] font-bold uppercase tracking-wider",
                    meta.color,
                  )}
                  title={`source: ${tag}`}
                >
                  <Icon className="h-2 w-2" />
                  {meta.label}
                </span>
              )
            })}
          </div>
        )}

        {/* Footer: branch info + logic count */}
        {(d.siblingCount > 1 || d.logicCount > 0) && (
          <div className="flex items-center justify-between mt-1.5 pt-1 border-t border-slate-700/30">
            {d.siblingCount > 1 && (
              <div className="flex items-center gap-1">
                <button
                  onClick={handlePrev}
                  disabled={d.siblingIndex === 0}
                  className="nodrag rounded p-0.5 text-rose-500/60 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30 disabled:cursor-default transition-colors"
                  aria-label="Previous sibling"
                >
                  <ChevronLeft className="h-2.5 w-2.5" />
                </button>
                <span className="text-[8px] font-bold text-rose-500/70 tabular-nums">
                  {d.siblingIndex + 1}/{d.siblingCount}
                </span>
                <button
                  onClick={handleNext}
                  disabled={d.siblingIndex === d.siblingCount - 1}
                  className="nodrag rounded p-0.5 text-rose-500/60 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30 disabled:cursor-default transition-colors"
                  aria-label="Next sibling"
                >
                  <ChevronRight className="h-2.5 w-2.5" />
                </button>
              </div>
            )}
            {d.logicCount > 0 && (
              <div className="flex items-center gap-1 ml-auto">
                <Brain className="h-2.5 w-2.5 text-rose-400/50" />
                <span className="text-[8px] font-bold text-rose-400/50">
                  {d.logicCount}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Branch-tip label — shown on leaf nodes, editable in-place. */}
        {d.isLeaf && (
          <BranchTipChip
            branchRootId={d.branchRootId}
            branchColor={d.branchColor}
            isActive={d.isActive}
            isTrunk={d.isTrunk}
            branchRootText={d.branchRootText}
          />
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
    </>
  )
}

/* ─── BranchTipChip — editable branch name anchored to leaf nodes ────────── */

interface BranchTipChipProps {
  branchRootId: string
  branchColor: string
  isActive: boolean
  isTrunk: boolean
  branchRootText: string
}

function deriveBranchLabel(isTrunk: boolean, text: string): string {
  if (isTrunk) return 'main'
  const clean = text.replace(/\s+/g, ' ').trim()
  if (!clean) return 'branch'
  // First ~4 words, capped at 28 chars.
  const words = clean.split(' ').slice(0, 4).join(' ')
  return words.length > 28 ? words.slice(0, 28) + '…' : words
}

function BranchTipChip({
  branchRootId,
  branchColor,
  isActive,
  isTrunk,
  branchRootText,
}: BranchTipChipProps) {
  const branchNames = useBranchStore((s) => s.branchNames)
  const setBranchName = useBranchStore((s) => s.setBranchName)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const customName = branchNames.get(branchRootId)
  const fallback = deriveBranchLabel(isTrunk, branchRootText)
  const displayName = customName || fallback

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    setDraft(customName ?? '')
    setEditing(true)
  }

  const commit = () => {
    setBranchName(branchRootId, draft)
    setEditing(false)
  }

  return (
    <div
      className="nodrag absolute left-1/2 -translate-x-1/2"
      style={{ bottom: -22 }}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.stopPropagation()}
    >
      {editing ? (
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            else if (e.key === 'Escape') setEditing(false)
          }}
          placeholder={fallback}
          className="text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border bg-[#0d1520] text-slate-100 outline-none focus:ring-1"
          style={{
            borderColor: branchColor,
            boxShadow: `0 0 0 1px ${branchColor}55`,
          }}
        />
      ) : (
        <button
          onClick={handleStartEdit}
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider transition-all",
            isActive ? "shadow-md" : "opacity-70 hover:opacity-100",
          )}
          style={{
            backgroundColor: isActive ? branchColor : 'transparent',
            color: isActive ? '#0d1520' : branchColor,
            border: `1.5px solid ${branchColor}`,
          }}
          title={customName ? `${customName} — click to rename` : `Click to name this branch`}
        >
          {isActive && <Check className="h-2.5 w-2.5" />}
          <span>{displayName}</span>
        </button>
      )}
    </div>
  )
}

// Stable reference — defined outside component
const nodeTypes: NodeTypes = { messageNode: MessageNodeComponent }

/* ─── Edge-style legend ─────────────────────────────────────────── */

const LEGEND_ITEMS: { kind: EdgeKind; label: string }[] = [
  { kind: 'direct',   label: 'Reply' },
  { kind: 'thinking', label: 'Thinking' },
  { kind: 'tool',     label: 'Tool' },
  { kind: 'source',   label: 'RAG / Web' },
]

function EdgeLegend() {
  const [open, setOpen] = useState(false)
  return (
    <div>
      {open ? (
        <div className="rounded-lg border border-slate-700/50 bg-[#0d1520]/95 backdrop-blur-md px-3 py-2 shadow-xl">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-400">Edge key</span>
            <button
              onClick={() => setOpen(false)}
              className="text-slate-500 hover:text-slate-300"
              aria-label="Close legend"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <div className="space-y-1">
            {LEGEND_ITEMS.map((item) => {
              const s = EDGE_STYLES[item.kind]
              return (
                <div key={item.kind} className="flex items-center gap-2">
                  <svg width="28" height="8" viewBox="0 0 28 8">
                    <line
                      x1="0" y1="4" x2="28" y2="4"
                      stroke={s.stroke}
                      strokeWidth={s.strokeWidth}
                      strokeDasharray={s.dasharray}
                    />
                  </svg>
                  <span className="text-[9px] text-slate-300">{item.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="rounded-lg border border-slate-700/50 bg-[#0d1520]/90 backdrop-blur-md px-2 py-1 shadow-md hover:border-slate-600 text-[8px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200 transition-colors"
          title="Edge style legend"
        >
          Edge key
        </button>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   ConversationTreeView — React Flow canvas
   ═══════════════════════════════════════════════════════════════════ */

export function ConversationTreeView({ allMessages, messages, status }: ConversationTreeViewProps) {
  const logicEntries = useSidebarStore((s) => s.logicEntries)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const branchSelections = useBranchStore((s) => s.branchSelections)
  const { selectBranch, nextBranch, prevBranch } = useBranchStore()

  // ReactFlow instance — captured on mount so scroll-to-HEAD can drive the viewport.
  const flowRef = useRef<ReactFlowInstance<MessageFlowNode, Edge> | null>(null)

  // Compact mode: collapses straight runs of ≥4 single-child messages into a
  // "… N messages …" pill. Persists per-thread (via localStorage); expand
  // state is session-local (resets on thread switch).
  const activeThreadId = useBranchStore((s) => s.activeThreadId)
  const COMPACT_STORAGE_PREFIX = 'rio:tree-compact:'
  const [compactMode, setCompactMode] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    try {
      return activeThreadId
        ? window.localStorage.getItem(COMPACT_STORAGE_PREFIX + activeThreadId) === '1'
        : false
    } catch { return false }
  })
  useEffect(() => {
    if (typeof window === 'undefined' || !activeThreadId) return
    try {
      const key = COMPACT_STORAGE_PREFIX + activeThreadId
      const stored = window.localStorage.getItem(key)
      setCompactMode(stored === '1')
    } catch {}
  }, [activeThreadId])
  const toggleCompact = useCallback(() => {
    setCompactMode((prev) => {
      const next = !prev
      if (typeof window !== 'undefined' && activeThreadId) {
        try {
          window.localStorage.setItem(COMPACT_STORAGE_PREFIX + activeThreadId, next ? '1' : '0')
        } catch {}
      }
      return next
    })
  }, [activeThreadId])
  const [expandedRunKeys, setExpandedRunKeys] = useState<Set<string>>(new Set())
  // Clear expanded runs when thread changes
  useEffect(() => { setExpandedRunKeys(new Set()) }, [activeThreadId])

  // Listen for click-to-expand dispatched by collapsed MessageNode variant.
  useEffect(() => {
    function handleExpand(e: Event) {
      const key = (e as CustomEvent<{ key: string }>).detail?.key
      if (!key) return
      setExpandedRunKeys((prev) => {
        const next = new Set(prev)
        next.add(key)
        return next
      })
    }
    window.addEventListener('rio:expand-run', handleExpand)
    return () => window.removeEventListener('rio:expand-run', handleExpand)
  }, [])

  // Right-click context menu state for git-style "travel back" actions.
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    messageId: string
  } | null>(null)

  React.useEffect(() => {
    if (!contextMenu) return
    const close = () => setContextMenu(null)
    window.addEventListener('click', close)
    window.addEventListener('keydown', close)
    return () => {
      window.removeEventListener('click', close)
      window.removeEventListener('keydown', close)
    }
  }, [contextMenu])

  const tree = useMemo(() => buildMessageTree(allMessages), [allMessages])
  const activePathIds = useMemo(() => {
    const path = tree.length > 0 ? getActivePath(tree, branchSelections) : messages
    return new Set(path.map((m) => m.id))
  }, [tree, branchSelections, messages])

  // Listen for in-node carousel clicks dispatched by MessageNodeComponent.
  // The custom-event bridge keeps node rendering free of tree-wide state.
  React.useEffect(() => {
    function handleBranchNav(e: Event) {
      const detail = (e as CustomEvent<{ direction: 'prev' | 'next'; messageId: string; parentId: string | null }>).detail
      if (!detail?.parentId) return
      const findNodeLocal = (nodes: MessageNode[], id: string): MessageNode | null => {
        for (const n of nodes) {
          if (n.message.id === id) return n
          const r = findNodeLocal(n.children, id)
          if (r) return r
        }
        return null
      }
      const node = findNodeLocal(tree, detail.messageId)
      if (!node) return
      const parent = findNodeLocal(tree, detail.parentId)
      const siblings = parent ? parent.children : null
      if (!siblings || siblings.length <= 1) return
      if (detail.direction === 'prev') prevBranch(detail.parentId, siblings)
      else nextBranch(detail.parentId, siblings)
    }
    window.addEventListener('rio:branch-nav', handleBranchNav)
    return () => window.removeEventListener('rio:branch-nav', handleBranchNav)
  }, [tree, nextBranch, prevBranch])

  const isStreaming = status === 'streaming' || status === 'submitted'

  // Convert tree → React Flow elements with lane-based layout
  // (each branch in its own vertical column, `git log --graph` style)
  const { flowNodes, flowEdges } = useMemo(() => {
    if (tree.length === 0) return { flowNodes: [], flowEdges: [] }
    const { nodes, edges } = treeToFlow(
      tree, activePathIds, selectedNodeId, logicEntries, allMessages, isStreaming,
      compactMode, expandedRunKeys,
    )
    const laid = applyLaneLayout(nodes, tree, activePathIds)
    return { flowNodes: laid, flowEdges: edges }
  }, [tree, activePathIds, selectedNodeId, logicEntries, allMessages, isStreaming, compactMode, expandedRunKeys])

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  // Sync when flowNodes/flowEdges change
  React.useEffect(() => { setNodes(flowNodes) }, [flowNodes, setNodes])
  React.useEffect(() => { setEdges(flowEdges) }, [flowEdges, setEdges])

  // Handle node click → select for detail panel
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId((prev) => prev === node.id ? null : node.id)
  }, [])

  // Handle node double-click → switch branch
  const onNodeDoubleClick = useCallback((_: React.MouseEvent, node: Node) => {
    const data = node.data as unknown as MessageNodeData
    if (data.parentId && !data.isActive) {
      selectBranch(data.parentId, node.id)
    }
  }, [selectBranch])

  // Handle right-click → open context menu for git-style travel-back actions
  const onNodeContextMenu = useCallback((e: React.MouseEvent, node: Node) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, messageId: node.id })
  }, [])

  const handleSwitchToBranch = useCallback((messageId: string) => {
    const findNodeLocal = (nodes: MessageNode[], id: string): MessageNode | null => {
      for (const n of nodes) {
        if (n.message.id === id) return n
        const r = findNodeLocal(n.children, id)
        if (r) return r
      }
      return null
    }
    const node = findNodeLocal(tree, messageId)
    if (node?.parentId) selectBranch(node.parentId, messageId)
    setContextMenu(null)
  }, [tree, selectBranch])

  // Selected message for detail panel
  const selectedMsg = selectedNodeId ? allMessages.find((m) => m.id === selectedNodeId) ?? null : null
  const selectedLogic = useMemo(() => {
    if (!selectedNodeId) return []
    const idx = allMessages.findIndex((m) => m.id === selectedNodeId)
    if (idx < 0) return []
    const msg = allMessages[idx]
    const nextMsg = idx + 1 < allMessages.length ? allMessages[idx + 1] : null
    return getLogicForMessage(msg, nextMsg, logicEntries)
  }, [selectedNodeId, allMessages, logicEntries])

  // Sources for the selected assistant turn. Real sources (when emitted by
  // the backend `source` SSE event) take precedence; otherwise fall back to
  // mock sources derived from tool-call logic entries so the card UI is
  // visible during development.
  const messageSourcesMap = useSidebarStore((s) => s.messageSources)
  const selectedSources = useMemo<MessageSource[]>(() => {
    if (!selectedNodeId || !selectedMsg) return []
    if (selectedMsg.role !== 'assistant') return []
    const fromStore = messageSourcesMap[selectedNodeId]
    if (fromStore && fromStore.length > 0) return fromStore
    return deriveMockSources(selectedLogic)
  }, [selectedNodeId, selectedMsg, messageSourcesMap, selectedLogic])

  // ── Scroll-to-HEAD ────────────────────────────────────────────────
  // HEAD = the last message on the active path. Pressing `h` (or the
  // button next to the legend) re-centers the viewport on that node.
  const activeTipId = messages.length > 0 ? messages[messages.length - 1].id : null

  const scrollToHead = useCallback(() => {
    const instance = flowRef.current
    if (!instance || !activeTipId) return
    const target = nodes.find((n) => n.id === activeTipId)
    if (!target) return
    instance.setCenter(
      target.position.x + NODE_WIDTH / 2,
      target.position.y + NODE_HEIGHT / 2,
      { zoom: 1, duration: 400 },
    )
  }, [nodes, activeTipId])

  // Bare `h` shortcut — guarded against editable fields and modifier keys.
  // Only active while the tree view is mounted.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== 'h' && e.key !== 'H') return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const target = e.target instanceof HTMLElement ? e.target : null
      const tag = target?.tagName
      const isEditable =
        tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable ||
        target?.closest('.monaco-editor') != null
      if (isEditable) return
      e.preventDefault()
      scrollToHead()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [scrollToHead])

  return (
    <div className="flex-1 flex overflow-hidden relative">
      <div className="flex-1 relative" style={{ height: '100%' }}>
        <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
          <EdgeLegend />
          <button
            onClick={scrollToHead}
            disabled={!activeTipId}
            className="rounded-lg border border-rose-500/40 bg-[#1a1520]/90 backdrop-blur-md px-2 py-1 shadow-md hover:border-rose-400 text-[8px] font-black uppercase tracking-[0.2em] text-rose-300 hover:text-rose-200 disabled:opacity-40 disabled:cursor-default transition-colors flex items-center gap-1"
            title="Scroll to HEAD — press H"
          >
            <Target className="h-2.5 w-2.5" />
            HEAD
          </button>
          <button
            onClick={toggleCompact}
            className={cn(
              "rounded-lg border bg-[#1a1520]/90 backdrop-blur-md px-2 py-1 shadow-md text-[8px] font-black uppercase tracking-[0.2em] transition-colors",
              compactMode
                ? "border-cyan-500/60 text-cyan-200 hover:border-cyan-400"
                : "border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-200",
            )}
            title={compactMode ? "Compact mode ON — click to expand all runs" : "Compact mode OFF — collapse long linear runs"}
            aria-pressed={compactMode}
          >
            Compact
          </button>
        </div>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onInit={(instance) => { flowRef.current = instance }}
          onNodeClick={onNodeClick}
          onNodeDoubleClick={onNodeDoubleClick}
          onNodeContextMenu={onNodeContextMenu}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.2}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
          className="bg-[#0c1524]"
        >
          <Background variant={BackgroundVariant.Lines} gap={30} size={1} color="#1a2a3d" />
          <Controls
            showInteractive={false}
            className="!bg-[#1a2332] !border-slate-700/50 !rounded-xl !shadow-xl [&>button]:!bg-[#1a2332] [&>button]:!border-slate-700/30 [&>button]:!text-slate-400 [&>button:hover]:!bg-slate-800 [&>button:hover]:!text-slate-200"
          />
          <MiniMap
            nodeColor={(node) => {
              const d = node.data as unknown as MessageNodeData
              if (d.isActive) return '#f43f5e'
              return '#334155'
            }}
            maskColor="rgba(0, 0, 0, 0.7)"
            className="!bg-[#0d1520] !border-slate-700/30 !rounded-xl"
          />
        </ReactFlow>
      </div>

      {/* Detail Panel */}
      {selectedMsg && (
        <DetailPanel
          message={selectedMsg}
          logicEntries={selectedLogic}
          sources={selectedSources}
          onClose={() => setSelectedNodeId(null)}
        />
      )}

      {/* Node context menu — git-style travel-back actions */}
      {contextMenu && (() => {
        const targetNode = allMessages.find((m) => m.id === contextMenu.messageId)
        const isActive = activePathIds.has(contextMenu.messageId)
        const findNodeLocal = (nodes: MessageNode[], id: string): MessageNode | null => {
          for (const n of nodes) {
            if (n.message.id === id) return n
            const r = findNodeLocal(n.children, id)
            if (r) return r
          }
          return null
        }
        const treeNode = findNodeLocal(tree, contextMenu.messageId)
        const canSwitch = !!treeNode?.parentId && !isActive
        return (
          <div
            role="menu"
            onClick={(e) => e.stopPropagation()}
            onContextMenu={(e) => e.preventDefault()}
            className="fixed z-50 min-w-[180px] rounded-lg border border-rose-900/50 bg-[#0d1520]/98 backdrop-blur-xl shadow-2xl py-1"
            style={{
              left: Math.min(contextMenu.x, window.innerWidth - 200),
              top: Math.min(contextMenu.y, window.innerHeight - 120),
            }}
          >
            <div className="px-3 py-1.5 border-b border-slate-800/60">
              <p className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-500">
                {targetNode?.role === 'assistant' ? 'Assistant' : 'User'} · {contextMenu.messageId.slice(0, 8)}
              </p>
            </div>
            {canSwitch && (
              <button
                role="menuitem"
                onClick={() => handleSwitchToBranch(contextMenu.messageId)}
                className="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-slate-200 hover:bg-sky-500/15 hover:text-sky-200 transition-colors"
              >
                <Compass className="h-3.5 w-3.5 text-sky-400" />
                <span className="flex-1 text-left">Switch to this branch</span>
              </button>
            )}
            {isActive && (
              <div className="flex items-center gap-2 px-3 py-2 text-[11px] text-emerald-300/70">
                <Check className="h-3.5 w-3.5" />
                <span>Currently on this path</span>
              </div>
            )}
          </div>
        )
      })()}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   DetailPanel
   ═══════════════════════════════════════════════════════════════════ */

interface DetailPanelProps {
  message: UIMessage
  logicEntries: LogicEntry[]
  sources: MessageSource[]
  onClose: () => void
}

function DetailPanel({ message, logicEntries, sources, onClose }: DetailPanelProps) {
  const isAssistant = message.role === 'assistant'
  const text = getMsgText(message)
  const sorted = [...logicEntries].sort((a, b) => a.timestamp - b.timestamp)
  const sortedSources = [...sources].sort((a, b) => a.timestamp - b.timestamp)

  return (
    <div className="w-80 border-l border-rose-900/20 bg-[#0d1520]/95 backdrop-blur-xl flex flex-col overflow-hidden flex-shrink-0">
      <div className="flex items-center justify-between p-4 border-b border-rose-900/20">
        <div className="flex items-center gap-2">
          {isAssistant ? <Bot className="h-4 w-4 text-rose-400" /> : <UserIcon className="h-4 w-4 text-rose-400" />}
          <span className={cn(
            "text-[10px] font-black uppercase tracking-[0.2em] text-rose-400",
          )}>
            {isAssistant ? 'Assistant' : 'User'} — Details
          </span>
        </div>
        <button onClick={onClose} className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-4 border-b border-rose-900/20">
        <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-6 break-words">{text}</p>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-5">
        {sortedSources.length > 0 && (
          <section>
            <h4 className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 mb-3">
              Sources ({sortedSources.length})
            </h4>
            <div className="space-y-3">
              {sortedSources.map((src, idx) => (
                <SourcePreviewCard
                  key={src.kind === 'web' ? `${src.kind}:${src.url}:${src.timestamp}:${idx}` : `${src.kind}:${src.filename}:${src.timestamp}:${idx}`}
                  source={src}
                />
              ))}
            </div>
          </section>
        )}

        <section>
        <h4 className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 mb-3">
          Thinking Steps ({sorted.length})
        </h4>
        {sorted.length === 0 ? (
          <p className="text-[10px] text-slate-600 text-center py-4">No thinking steps recorded</p>
        ) : (
          <div className="space-y-2">
            {sorted.map((entry) => {
              const Icon = LOGIC_ICONS[entry.kind] ?? Info
              const color = LOGIC_COLORS[entry.kind] ?? 'text-slate-400'
              return (
                <div key={entry.id} className="flex items-start gap-2 rounded-lg px-2.5 py-2 bg-white/[0.02] border border-slate-800/50">
                  <Icon className={cn('h-3 w-3 mt-0.5 flex-shrink-0', color)} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] font-bold text-slate-300 leading-tight">{entry.title}</p>
                    {entry.detail && (
                      <p className="text-[9px] text-slate-500 mt-0.5 leading-snug break-words">{entry.detail}</p>
                    )}
                    <p className="text-[7px] font-mono text-slate-600 mt-0.5">
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        </section>
      </div>
    </div>
  )
}
