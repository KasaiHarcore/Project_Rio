import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import { cn } from '@/shared/lib/utils'
import { User, ArrowRight, Target, Upload } from 'lucide-react'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/shared/lib/agent-config'
import { SmartDataCard } from './SmartDataCard'
import { SQLApprovalCard } from './SQLApprovalCard'
import { useSQLApprovalStore } from '@/shared/store/sql-approval-store'
import { CHARACTERS, type CharacterId } from '@/types/character'
import { TypingIndicator } from '@/components/ui/typing-indicator'
import { useEmotionalStore, type Mood } from '@/features/emotional/store'
import Image from 'next/image'
import { useRouter } from 'next/navigation'

/** Format a Date to a short local time string, e.g. "14:32" or "02:32 PM". */
function formatMessageTime(d?: Date | null): string {
  if (!d || isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface ChatListProps {
  messages: UIMessage[]
  isLoading?: boolean
  /** Chat status from useChat: ready | streaming | submitted | error */
  status?: 'ready' | 'streaming' | 'submitted' | 'error'
}

// ── Mood-Aware Greetings ────────────────────────────────────────────────
function getMoodGreeting(mood: Mood): string {
  const greetings: Record<Mood, string> = {
    happy: "Neural link ready!",
    excited: "Let's do this, Sensei!",
    neutral: "System online.",
    sad: "...I'm here if you need me.",
    frustrated: "Connection stable. Ready when you are.",
    tired: "Low power mode active..."
  }
  return greetings[mood] || "Neural link established."
}

export function ChatList({ messages, isLoading, status }: ChatListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { mood, fetchState } = useEmotionalStore()
  const router = useRouter()

  useEffect(() => {
    fetchState('rio')
  }, [fetchState])

  useEffect(() => {
    // Smooth scroll during streaming, instant jump otherwise
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({
        behavior: status === 'streaming' ? 'smooth' : 'auto',
        block: 'end',
      })
    }
  }, [messages, status])

  const greeting = getMoodGreeting(mood)

  // Empty state when no messages
  if (messages.length === 0) {
    return (
      <section ref={scrollRef} role="status" aria-label="Waiting for messages" className="flex-1 overflow-y-auto p-6 lg:p-12 flex items-center justify-center">
        <div className="text-center max-w-md">
          {/* Agent Avatar with Mood */}
          <div className="mx-auto mb-6 relative group w-fit">
            <div className="absolute inset-0 rounded-2xl blur-xl opacity-20 group-hover:opacity-40 transition-opacity bg-[var(--empty-glow)]"></div>
            <div className="relative w-32 h-32 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 p-2 shadow-[0_0_30px_rgba(79,70,229,0.3)]">
              <div className="w-full h-full rounded-xl bg-indigo-950 overflow-hidden relative">
                <Image
                  src="/images/avatar.png"
                  alt="Rio"
                  fill
                  className="object-contain"
                />
              </div>
            </div>
          </div>

          {/* Mood-Aware Welcome Text */}
          <h2 className="text-xl font-black mb-2 tracking-tight text-[var(--empty-title)]">
            {greeting}
          </h2>
          <p className="text-sm mb-8 font-medium leading-relaxed text-[var(--empty-text)]">
            System ready. Initialization complete.<br/>
            Waiting for direct command input...
          </p>

          {/* Quick Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 mt-8 mb-6">
            <button
              onClick={() => {
                const lastThreadId = localStorage.getItem('last-thread-id')
                if (lastThreadId) {
                  router.push(`/operation?thread=${lastThreadId}`)
                } else {
                  router.push('/operation')
                }
              }}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <ArrowRight size={16} />
              Resume Last Chat
            </button>
            <button
              onClick={() => router.push('/mission?new=true')}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <Target size={16} />
              Start Mission
            </button>
            <button
              onClick={() => router.push('/knowledge')}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-primary/50 text-sm font-bold text-white transition-all"
            >
              <Upload size={16} />
              Upload Document
            </button>
          </div>

          {/* Status Indicator */}
          <div
            className="inline-flex items-center gap-3 rounded-lg border px-4 py-2 shadow-sm transition-all hover:scale-105 backdrop-blur-sm bg-[var(--empty-indicator-bg)] border-[var(--empty-indicator-border)]"
            style={{ boxShadow: 'var(--empty-indicator-shadow)' }}
          >
            <div className="h-2 w-2 rounded-full animate-pulse bg-[var(--empty-dot)]" style={{ boxShadow: `0 0 8px var(--empty-dot-glow)` }}></div>
            <span className="font-mono text-[10px] font-bold uppercase text-[var(--empty-label-text)]">
                Awaiting Orders • {mood}
            </span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={scrollRef} role="log" aria-label="Chat messages" className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-6 scroll-smooth custom-scrollbar">
      {messages.map((m, idx) => {
        const isAssistant = m.role === 'assistant';
        const msgCharacterId = (m as any).character_id as CharacterId | undefined;
        const characterName = msgCharacterId
          ? CHARACTERS.find(c => c.id === msgCharacterId)?.name
          : undefined;

        // Show blinking cursor on the last assistant message while streaming
        const isLastAssistant = isAssistant && idx === messages.length - 1;
        const showStreamingCursor = isLastAssistant && status === 'streaming';

        return (
          <div key={m.id} className={cn("group mx-auto flex max-w-5xl items-start gap-4", !isAssistant && "flex-row-reverse")}>

            {/* Avatar Column */}
            <div className="flex flex-col items-center flex-shrink-0 mt-1 gap-1">
              {isAssistant ? (
                <>
                  <AgentMessageAvatar characterId={msgCharacterId} />
                  {characterName && (
                    <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-wider">{characterName}</span>
                  )}
                </>
              ) : (
                <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-colors bg-[var(--user-avatar-bg)] border-[var(--user-avatar-border)]">
                  <User className="h-5 w-5 text-[var(--user-avatar-icon)]" />
                </div>
              )}
            </div>

            {/* Content Column (Smart Card) */}
            <div className="flex-1 min-w-0 max-w-[85%]">
                <SmartDataCard
                    role={m.role as any}
                    content={m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || (m as any).content || ''}
                    timestamp={formatMessageTime((m as any).createdAt)}
                    senderName={isAssistant ? (characterName ?? 'SYSTEM_RESPONSE') : 'Sensei'}
                    isStreaming={showStreamingCursor}
                />
            </div>
          </div>
        )
      })}

      {/* SQL Approval Card — shown when an interrupt is pending */}
      <SQLApprovalCardWrapper />

      {/* Typing indicator — shown when waiting for first token (submitted state) */}
      {status === 'submitted' && <TypingIndicator />}

      {/* Fallback loading skeleton for history loading (no status available) */}
      {isLoading && status !== 'submitted' && status !== 'streaming' && (
          <div className="mx-auto flex max-w-5xl items-start gap-4">
               <div className="h-14 w-14 rounded-2xl bg-muted/60 animate-pulse flex-shrink-0" />
               <div className="flex-1 space-y-3 pt-1">
                 <div className="h-4 w-28 rounded-lg bg-muted/60 animate-pulse" />
                 <div className="rounded-2xl border border-border/50 p-5 space-y-2.5">
                   <div className="h-3.5 w-full rounded bg-muted/50 animate-pulse" />
                   <div className="h-3.5 w-[85%] rounded bg-muted/50 animate-pulse delay-75" />
                   <div className="h-3.5 w-[60%] rounded bg-muted/50 animate-pulse delay-150" />
                 </div>
               </div>
          </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} className="h-4" />
    </section>
  )
}

/** Renders the SQLApprovalCard only when there is a pending approval. */
function SQLApprovalCardWrapper() {
  const pending = useSQLApprovalStore((s) => s.pending)
  if (!pending) return null
  return (
    <div className="py-3">
      <SQLApprovalCard />
    </div>
  )
}
