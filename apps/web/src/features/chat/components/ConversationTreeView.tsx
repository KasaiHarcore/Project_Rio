"use client"

import React, { useState, useMemo, useCallback } from 'react'
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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { cn } from '@/shared/lib/utils'
import type { UIMessage } from 'ai'
import {
  User as UserIcon, Bot, Brain, Route, Wrench, Info,
  X, Loader2, ChevronLeft, ChevronRight,
  Database, Globe, Code2, Sparkles,
  GitBranch, Check, Compass,
} from 'lucide-react'
import { useSidebarStore, type LogicEntry } from '@/features/chat/store'
import { buildMessageTree, getActivePath, type MessageNode } from '@/features/chat/lib/message-tree'
import { useBranchStore } from '@/features/chat/stores/branch-store'

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

/* ─── Dagre layout ───────────────────────────────────────────────── */

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

function treeToFlow(
  roots: MessageNode[],
  activePathIds: Set<string>,
  selectedNodeId: string | null,
  logicEntries: LogicEntry[],
  allMessages: UIMessage[],
  isStreaming: boolean,
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

  function walk(node: MessageNode) {
    const msg = node.message
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

      edges.push({
        id: `e-${msg.id}-${child.message.id}`,
        source: msg.id,
        target: child.message.id,
        type: 'smoothstep',
        animated: isActiveBranch && kind !== 'direct',
        style: {
          stroke: base.stroke,
          strokeWidth: isActiveBranch ? base.strokeWidth + 0.5 : base.strokeWidth,
          strokeDasharray: base.dasharray,
          opacity: isActiveBranch ? 1 : 0.3,
        },
        data: { kind },
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

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
      <div
        data-active={d.isActive ? '1' : '0'}
        className={cn(
          "w-[240px] rounded-lg border-2 px-3 py-2.5 transition-all cursor-pointer",
          d.isSelected
            ? "ring-2 ring-rose-500 border-rose-500 bg-[#1a1520] shadow-[0_0_20px_rgba(244,63,94,0.55)]"
            : d.isActive
              ? cn(accentBorder, "bg-[#1a1520]/95 shadow-[0_0_12px_rgba(244,63,94,0.35)]")
              : cn(accentBorder, "bg-[#1a1520]/40 opacity-30 hover:opacity-70"),
        )}
      >
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
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
    </>
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
    <div className="absolute top-3 left-3 z-10">
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

export function ConversationTreeView({ allMessages, messages, status, onExitTreeView }: ConversationTreeViewProps) {
  const logicEntries = useSidebarStore((s) => s.logicEntries)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const branchSelections = useBranchStore((s) => s.branchSelections)
  const setPendingBranchParent = useBranchStore((s) => s.setPendingBranchParent)
  const { selectBranch, nextBranch, prevBranch } = useBranchStore()

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

  // Convert tree → React Flow elements with dagre layout
  const { flowNodes, flowEdges } = useMemo(() => {
    if (tree.length === 0) return { flowNodes: [], flowEdges: [] }
    const { nodes, edges } = treeToFlow(tree, activePathIds, selectedNodeId, logicEntries, allMessages, isStreaming)
    const laid = layoutWithDagre(nodes, edges)
    return { flowNodes: laid, flowEdges: edges }
  }, [tree, activePathIds, selectedNodeId, logicEntries, allMessages, isStreaming])

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

  const handleBranchFromHere = useCallback((messageId: string) => {
    const msg = allMessages.find((m) => m.id === messageId)
    if (!msg) return
    const preview = (() => {
      const text = msg.parts
        ?.filter((p: any) => p.type === 'text')
        .map((p: any) => p.text)
        .join('') || (msg as any).content || ''
      const clean = text.replace(/\s+/g, ' ').trim()
      return clean.length > 80 ? clean.slice(0, 80) + '…' : clean
    })()
    setPendingBranchParent({
      messageId,
      preview,
      role: msg.role,
    })
    setContextMenu(null)
    onExitTreeView?.()
  }, [allMessages, setPendingBranchParent, onExitTreeView])

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

  return (
    <div className="flex-1 flex overflow-hidden relative">
      <div className="flex-1 relative" style={{ height: '100%' }}>
        <EdgeLegend />
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
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
            <button
              role="menuitem"
              onClick={() => handleBranchFromHere(contextMenu.messageId)}
              className="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-slate-200 hover:bg-rose-500/15 hover:text-rose-200 transition-colors"
            >
              <GitBranch className="h-3.5 w-3.5 text-rose-400" />
              <span className="flex-1 text-left">Branch from here</span>
            </button>
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
  onClose: () => void
}

function DetailPanel({ message, logicEntries, onClose }: DetailPanelProps) {
  const isAssistant = message.role === 'assistant'
  const text = getMsgText(message)
  const sorted = [...logicEntries].sort((a, b) => a.timestamp - b.timestamp)

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

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
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
      </div>
    </div>
  )
}
