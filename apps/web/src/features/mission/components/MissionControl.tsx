"use client"

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { ChatList } from "@/features/chat/components/ChatList"
import { ChatInput } from "@/features/chat/components/ChatInput"
import { ChatSidebar } from "@/features/chat/components/ChatSidebar"
import { OperationalHUD } from "@/features/chat/components/OperationalHUD"
import { ConversationTreeView } from "@/features/chat/components/ConversationTreeView"
import { useChat } from '@ai-sdk/react'
import type { ChatRequestOptions, UIMessage } from 'ai'
import { useUIStore } from '@/shared/store/ui-store'
import { apiGetThreadMessages, apiRegenerateMessage, MessageRecord } from '@/features/chat/api'
import { createSidebarTransport } from '@/features/chat/lib/chat-transport'
import { buildMessageTree, getActivePath, type BranchSelections } from '@/features/chat/lib/message-tree'
import { useBranchStore } from '@/features/chat/stores/branch-store'
import { useStreamSidebarReset } from '@/features/chat/hooks/use-stream-sidebar'
import { useSidebarStore } from '@/features/chat/store'
import { useAffinityTracker } from '@/features/emotional/hooks/use-affinity-tracker'

interface MissionControlProps {
  /** Thread ID to load. '__new__' for a fresh chat, or an existing thread UUID. */
  threadId?: string | null
  /** Called when the user presses back. If not provided, falls back to endMission (dashboard). */
  onBack?: () => void
  /** Called when a brand-new thread is created by the backend (passes the new thread_id). */
  onThreadCreated?: (newThreadId: string) => void
  /** Called after an AI response finishes so the parent can refresh data. */
  onMessageComplete?: () => void
}

/** Convert backend MessageRecord[] → UIMessage[] for useChat.
 *  AI SDK v6 UIMessage has: id, role, parts (no content, no createdAt).
 *  We attach `createdAt` as an extra property so the chat list can show
 *  real timestamps from the database. */
function toUIMessages(records: MessageRecord[]): UIMessage[] {
  return records.map((r) => {
    const msg: UIMessage = {
      id: r.id,
      role: r.role as 'user' | 'assistant',
      parts: [{ type: 'text' as const, text: r.content }],
    };
    // Attach backend timestamp so ChatList can display it
    if (r.created_at) {
      (msg as any).createdAt = new Date(r.created_at);
    }
    // Attach persona so ChatList can render the correct avatar
    if (r.character_id) {
      (msg as any).character_id = r.character_id;
    }
    // Attach parent_id for branching tree
    if (r.parent_id) {
      (msg as any).parentId = r.parent_id;
    }
    return msg;
  })
}

export function MissionControl({ threadId, onBack, onThreadCreated, onMessageComplete }: MissionControlProps) {
  const [input, setInput] = useState('')
  const [missionSuggestion, setMissionSuggestion] = useState<{ show: boolean; topic: string } | null>(null)
  const chatKey = useUIStore((state) => state.chatKey)
  const endMission = useUIStore((state) => state.endMission)
  const agentMode = useUIStore((state) => state.agentMode)
  const { recordMessage } = useAffinityTracker()

  // Character persona — sent to backend for persona-aware responses
  const activeCharacterId = 'rio'

  const isNewChat = !threadId || threadId === '__new__'
  const [resolvedThreadId, setResolvedThreadId] = useState<string | null>(null)

  // Instance-scoped captured thread ID — replaces the old module-level global.
  // This prevents cross-session contamination when multiple chats exist or
  // the user rapidly switches threads.
  const capturedThreadIdRef = useRef<string | null>(null)

  // Track loading state for existing threads
  const [historyLoading, setHistoryLoading] = useState(false)
  const loadedThreadRef = useRef<string | null>(null)

  const effectiveThreadId = threadId && threadId !== '__new__' ? threadId : resolvedThreadId

  // Reset sidebar when starting a new chat or switching threads
  useStreamSidebarReset(isNewChat, threadId)

  // ── Refs for latest values (closures in transport body resolver) ──
  const effectiveThreadIdRef = useRef(effectiveThreadId)
  effectiveThreadIdRef.current = effectiveThreadId
  const agentModeRef = useRef(agentMode)
  agentModeRef.current = agentMode
  const characterRef = useRef(activeCharacterId)
  characterRef.current = activeCharacterId

  // ── Sidebar-aware transport (stable — only created once) ──
  const transport = useMemo(
    () =>
      createSidebarTransport(
        () => {
          // Fork intent (from "Branch from here"): apply once, then clear.
          const pending = useBranchStore.getState().consumePendingBranchParent()
          return {
            ...(effectiveThreadIdRef.current
              ? { thread_id: effectiveThreadIdRef.current }
              : {}),
            mode: agentModeRef.current,
            character: characterRef.current,
            ...(pending ? { parent_message_id: pending.messageId } : {}),
          }
        },
        (id) => { capturedThreadIdRef.current = id },
      ),
    [],
  )

  // Chat ID for useChat — unique per thread or per new-chat session.
  // IMPORTANT: useState initializer ensures the ID is stable across the
  // component's lifetime.  When a new thread is created mid-conversation
  // (effectiveThreadId transitions from null → uuid), the chatId must NOT
  // change, otherwise useChat treats it as a brand-new chat and drops all
  // messages.  The key={missionKey} on the parent already handles explicit
  // navigation — a remount will re-run the initializer with the correct value.
  const [chatId] = useState(() =>
    effectiveThreadId ? `thread-${effectiveThreadId}` : `new-${chatKey}`
  )

  const { messages: rawMessages, sendMessage, setMessages, status } = useChat({
    id: chatId,
    transport,
    onFinish: () => {
      const captured = capturedThreadIdRef.current
      if (captured && !effectiveThreadIdRef.current) {
        setResolvedThreadId(captured)
        onThreadCreated?.(captured)
      }
      onMessageComplete?.()
    },
  })

  // Stamp every message with a createdAt date and character_id if missing.
  // For history messages these were set in toUIMessages(); for new real-time
  // messages (user sends or AI streams) we stamp them the first time they appear.
  const timestampMap = useRef<Map<string, Date>>(new Map())
  const characterMap = useRef<Map<string, string>>(new Map())
  const messages = useMemo(() => {
    return rawMessages.map((m) => {
      const needsTimestamp = !(m as any).createdAt
      const needsCharacter = m.role === 'assistant' && !(m as any).character_id
      if (!needsTimestamp && !needsCharacter) return m

      const stamped = { ...m } as any
      if (needsTimestamp) {
        if (!timestampMap.current.has(m.id)) {
          timestampMap.current.set(m.id, new Date())
        }
        stamped.createdAt = timestampMap.current.get(m.id)
      }
      if (needsCharacter) {
        if (!characterMap.current.has(m.id)) {
          characterMap.current.set(m.id, activeCharacterId)
        }
        stamped.character_id = characterMap.current.get(m.id)
      }
      return stamped as typeof m
    })
  }, [rawMessages, activeCharacterId])

  // ── All messages (all branches) for tree building ──
  // useChat only holds the ACTIVE PATH so the agent doesn't see conflicting
  // branches.  The full message set is stored here for the tree UI.
  const [allBranchMessages, setAllBranchMessages] = useState<UIMessage[]>([])

  // Keep allBranchMessages in sync with live messages from useChat.
  // During a conversation, new user/assistant messages arrive via the stream
  // and are added to `messages` but NOT to `allBranchMessages`.  This effect
  // merges them so the tree view updates in real-time.
  const allBranchRef = useRef(allBranchMessages)
  allBranchRef.current = allBranchMessages
  useEffect(() => {
    if (messages.length === 0) return
    const existingIds = new Set(allBranchRef.current.map((m) => m.id))
    const newMsgs = messages.filter((m) => !existingIds.has(m.id))
    if (newMsgs.length > 0) {
      setAllBranchMessages((prev) => [...prev, ...newMsgs])
    }
  }, [messages])

  // Helper: given all records, build tree, compute active path, set into useChat.
  // Also restores persisted logic entries (agent process info) into the sidebar store.
  const loadMessagesIntoChat = useCallback((records: MessageRecord[], selections?: BranchSelections) => {
    const allUIMessages = toUIMessages(records)
    setAllBranchMessages(allUIMessages)
    // Build tree and extract active path for useChat
    const tree = buildMessageTree(allUIMessages)
    const sel = selections ?? useBranchStore.getState().branchSelections
    const activePath = tree.length > 0 ? getActivePath(tree, sel) : allUIMessages
    setMessages(activePath)

    // Restore persisted logic entries from message metadata
    const sidebar = useSidebarStore.getState()
    sidebar.clearLogicEntries()
    for (const rec of records) {
      const entries = rec.metadata?.logic_entries
      if (Array.isArray(entries)) {
        for (let i = 0; i < entries.length; i++) {
          const e = entries[i]
          if (e?.title) {
            sidebar.addLogicEntry({
              title: e.title,
              detail: e.detail ?? undefined,
              kind: e.kind ?? 'info',
            })
          }
        }
      }
    }
  }, [setMessages])

  // Load message history when threadId points to an existing thread.
  // IMPORTANT: In AI SDK v6 the `messages` prop in useChat is only read
  // once (when the Chat instance is created).  To load history into an
  // existing Chat we must use the imperative `setMessages` from useChat.
  //
  // NOTE: `resolvedThreadId` is intentionally EXCLUDED from the dependency
  // array.  It is read inside the effect as a guard to skip history reload
  // when transitioning from __new__ → UUID (the messages are already in the
  // chat from the current session).  If we included it, the effect would
  // re-run when resolvedThreadId is set while threadId is still '__new__',
  // hitting the first branch and clearing messages mid-conversation.
  useEffect(() => {
    if (!threadId || threadId === '__new__') {
      setMessages([])
      setAllBranchMessages([])
      setResolvedThreadId(null)
      loadedThreadRef.current = null
      capturedThreadIdRef.current = null
      useBranchStore.getState().setActiveThread(null)
      return
    }

    if (loadedThreadRef.current === threadId) return
    // Skip history reload when transitioning from __new__ → UUID after thread creation.
    // The messages are already in the chat from the current session.
    if (resolvedThreadId && resolvedThreadId === threadId) return

    let cancelled = false
    setHistoryLoading(true)

    // Load persisted branch selections for this thread BEFORE rendering history
    // so getActivePath walks the correct branches on first paint.
    useBranchStore.getState().setActiveThread(threadId)

    apiGetThreadMessages(threadId).then(({ messages: records }) => {
      if (cancelled) return
      loadedThreadRef.current = threadId
      setResolvedThreadId(threadId)
      loadMessagesIntoChat(records)
    }).catch(() => {
      if (cancelled) return
      setMessages([])
      setAllBranchMessages([])
    }).finally(() => {
      if (!cancelled) setHistoryLoading(false)
    })

    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- resolvedThreadId excluded intentionally (see comment above)
  }, [threadId, setMessages, loadMessagesIntoChat])

  // Sync active thread in branch store when a new thread is created mid-conversation
  // (e.g. __new__ → UUID after first message). Ensures new selections persist to the
  // correct thread-scoped storage key.
  useEffect(() => {
    if (!resolvedThreadId) return
    useBranchStore.getState().setActiveThread(resolvedThreadId)
  }, [resolvedThreadId])

  // Load persisted notes when opening an existing thread
  useEffect(() => {
    if (!threadId || threadId === '__new__') return
    let cancelled = false
    fetch(`/api/notes?thread_id=${threadId}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((notes: Array<{ id: string; content: string; todos?: { text: string; done: boolean }[]; pinned: boolean; source: string }>) => {
        if (cancelled || !notes?.length) return
        const store = useSidebarStore.getState()
        for (const n of notes) {
          store.addStickyNote({
            content: n.content,
            todos: n.todos,
            author: n.source === 'agent' ? 'agent' : 'user',
            dbId: n.id,
          })
        }
      })
      .catch(() => { })
    return () => { cancelled = true }
  }, [threadId])

  // Map AI status to HUD status types
  const hudStatus = status === 'ready' ? 'ready' : status === 'error' ? 'error' : status === 'streaming' ? 'streaming' : 'submitted'

  const isLoading = status === 'submitted' || status === 'streaming'

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>, chatRequestOptions?: ChatRequestOptions) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage({ text: input }, chatRequestOptions)
    recordMessage() // Award affinity for sending a message
    setInput('')
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }

  const handleBack = onBack ?? endMission

  // ── Message tree for branching ──────────────────────────────────
  // Tree is built from ALL messages (all branches). The active path
  // (already set into useChat) is what gets displayed, but we need the
  // full tree for the branch selector UI.
  const branchSelections = useBranchStore((s) => s.branchSelections)
  const messageTree = useMemo(() => buildMessageTree(allBranchMessages), [allBranchMessages])

  // When the user switches branches, recompute the active path and
  // update useChat so the agent only sees the selected branch.
  const prevSelectionsRef = useRef(branchSelections)
  useEffect(() => {
    if (prevSelectionsRef.current === branchSelections) return
    prevSelectionsRef.current = branchSelections
    if (messageTree.length === 0) return
    const activePath = getActivePath(messageTree, branchSelections)
    setMessages(activePath)
  }, [branchSelections, messageTree, setMessages])

  const [regenerating, setRegenerating] = useState(false)

  const handleRegenerate = useCallback(async (userMessageId: string) => {
    if (!effectiveThreadId || regenerating) return
    setRegenerating(true)
    try {
      const res = await apiRegenerateMessage(effectiveThreadId, userMessageId, activeCharacterId)
      if (!res.ok) throw new Error('Regeneration failed')
      // Wait for stream to finish, then reload messages with new branch
      const reader = res.body?.getReader()
      if (reader) {
        while (true) {
          const { done } = await reader.read()
          if (done) break
        }
      }
      // Reload all messages to pick up the new branch
      const { messages: records } = await apiGetThreadMessages(effectiveThreadId)
      loadMessagesIntoChat(records)
    } catch {
      // silently fail
    } finally {
      setRegenerating(false)
    }
  }, [effectiveThreadId, regenerating, activeCharacterId, loadMessagesIntoChat])

  // ── Tree view toggle ──────────────────────────────────────────────
  const [treeView, setTreeView] = useState(false)
  const toggleTreeView = useCallback(() => setTreeView((v) => !v), [])

  const hudTitle = effectiveThreadId
    ? `OP: ${effectiveThreadId.substring(0, 8).toUpperCase()}`
    : 'NEW_OPERATION'

  return (
    <div className="flex flex-1 min-w-0 overflow-hidden h-full relative">
      {/* Main Chat Content */}
      <div className="flex-1 min-w-0 flex flex-col relative z-10 backdrop-blur-sm bg-[var(--mission-ctrl-bg)]">

        {/* Superior Operational HUD */}
        <OperationalHUD
          status={hudStatus}
          title={hudTitle}
          onBack={handleBack}
          messages={messages}
          treeView={treeView}
          onToggleTreeView={toggleTreeView}
        />

        {treeView ? (
          <ConversationTreeView
            allMessages={allBranchMessages}
            messages={messages}
            status={hudStatus}
          />
        ) : (
          <>
            <ChatList
              messages={messages}
              isLoading={isLoading || historyLoading}
              status={hudStatus}
              messageTree={messageTree}
              onRegenerate={handleRegenerate}
              regenerating={regenerating}
            />

            <PendingBranchBanner />

            <ChatInput
              input={input}
              handleInputChange={handleInputChange}
              handleSubmit={handleSubmit}
              isLoading={isLoading}
            />
          </>
        )}
      </div>

      {/* Right Sidebar (Chat details) */}
      <ChatSidebar messages={messages} status={hudStatus} threadId={effectiveThreadId ?? null} treeView={treeView} onToggleTreeView={toggleTreeView} />
    </div>
  )
}

/**
 * PendingBranchBanner — shows above ChatInput when the user has clicked
 * "Branch from here" on a message. Indicates that the next sent message
 * will fork off that parent. Clicking Cancel clears the intent.
 */
function PendingBranchBanner() {
  const pending = useBranchStore((s) => s.pendingBranchParent)
  const setPendingBranchParent = useBranchStore((s) => s.setPendingBranchParent)

  if (!pending) return null

  const roleLabel = pending.role === 'assistant' ? 'Rio' : pending.role === 'user' ? 'Sensei' : pending.role

  return (
    <div
      role="status"
      aria-live="polite"
      className="mx-auto max-w-5xl px-4 lg:px-0 pb-2"
    >
      <div className="flex items-center gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs">
        <span className="font-mono text-[9px] font-bold uppercase tracking-wider text-rose-400 flex-shrink-0">
          Branching
        </span>
        <span className="flex-1 min-w-0 truncate text-rose-100/90">
          <span className="text-rose-300/70">From {roleLabel}:</span>{' '}
          <span>{pending.preview || '(empty message)'}</span>
        </span>
        <button
          onClick={() => setPendingBranchParent(null)}
          className="flex-shrink-0 rounded px-2 py-0.5 text-[10px] font-bold uppercase text-rose-300 hover:text-rose-100 hover:bg-rose-500/20 transition-colors"
          aria-label="Cancel branch"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
