"use client"

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { ChatList } from "@/components/features/chat/ChatList"
import { ChatInput } from "@/components/features/chat/ChatInput"
import { ChatSidebar } from "@/components/features/chat/ChatSidebar"
import { OperationalHUD } from "@/components/features/chat/OperationalHUD"
import { useChat } from '@ai-sdk/react'
import type { ChatRequestOptions, UIMessage } from 'ai'
import { useUIStore } from '@/store/ui-store'
import { apiGetThreadMessages, MessageRecord } from '@/lib/api'
import { createSidebarTransport, getCapturedThreadId, setCapturedThreadId } from '@/lib/chat-transport'
import { useStreamSidebarReset } from '@/hooks/use-stream-sidebar'
import { useSidebarStore } from '@/store/sidebar-store'
import { useAffinityTracker } from '@/hooks/use-affinity-tracker'

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

  // Track the resolved thread ID (may start null for new chats, then set by backend)
  const isNewChat = !threadId || threadId === '__new__'
  const [resolvedThreadId, setResolvedThreadId] = useState<string | null>(isNewChat ? null : threadId!)

  // Track loading state for existing threads
  const [historyLoading, setHistoryLoading] = useState(false)
  const loadedThreadRef = useRef<string | null>(null)

  // Determine effective thread ID (from props or resolved from backend)
  const effectiveThreadId = threadId && threadId !== '__new__' ? threadId : resolvedThreadId

  // Reset sidebar when starting a new chat
  useStreamSidebarReset(isNewChat)

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
      createSidebarTransport(() => ({
        ...(effectiveThreadIdRef.current
          ? { thread_id: effectiveThreadIdRef.current }
          : {}),
        mode: agentModeRef.current,
        character: characterRef.current,
      })),
    [],
  )

  // Chat ID for useChat — unique per thread or per new-chat session
  const chatId = effectiveThreadId ? `thread-${effectiveThreadId}` : `new-${chatKey}`

  const { messages: rawMessages, sendMessage, setMessages, status } = useChat({
    id: chatId,
    transport,
    onFinish: () => {
      // Capture the thread ID from the transport (set by sidebarFetch)
      const captured = getCapturedThreadId()
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

  // Load message history when threadId points to an existing thread.
  // IMPORTANT: In AI SDK v6 the `messages` prop in useChat is only read
  // once (when the Chat instance is created).  To load history into an
  // existing Chat we must use the imperative `setMessages` from useChat.
  useEffect(() => {
    if (!threadId || threadId === '__new__') {
      setMessages([])
      setResolvedThreadId(null)
      loadedThreadRef.current = null
      setCapturedThreadId(null)
      return
    }

    if (loadedThreadRef.current === threadId) return

    let cancelled = false
    setHistoryLoading(true)

    apiGetThreadMessages(threadId).then(({ messages: records }) => {
      if (cancelled) return
      loadedThreadRef.current = threadId
      setResolvedThreadId(threadId)
      setMessages(toUIMessages(records))
    }).catch(() => {
      if (cancelled) return
      setMessages([])
    }).finally(() => {
      if (!cancelled) setHistoryLoading(false)
    })

    return () => { cancelled = true }
  }, [threadId, setMessages])

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

  const hudTitle = effectiveThreadId
    ? `OP: ${effectiveThreadId.substring(0, 8).toUpperCase()}`
    : 'NEW_OPERATION'

  return (
    <div className="flex flex-1 overflow-hidden h-full relative">
      {/* Main Chat Content */}
      <div className="flex-1 flex flex-col relative z-10 w-full max-w-full backdrop-blur-sm bg-[var(--mission-ctrl-bg)]">

        {/* Superior Operational HUD */}
        <OperationalHUD
          status={hudStatus}
          title={hudTitle}
          onBack={handleBack}
          messages={messages}
        />

        <ChatList
          messages={messages}
          isLoading={isLoading || historyLoading}
          status={hudStatus}
        />

        <ChatInput
          input={input}
          handleInputChange={handleInputChange}
          handleSubmit={handleSubmit}
          isLoading={isLoading}
        />
      </div>

      {/* Right Sidebar (Chat details) */}
      <ChatSidebar messages={messages} status={hudStatus} threadId={effectiveThreadId ?? null} />
    </div>
  )
}
