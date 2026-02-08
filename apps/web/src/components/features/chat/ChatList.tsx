import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import { cn } from '@/lib/utils'
import { User } from 'lucide-react'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/lib/agent-config'
import { SmartDataCard } from './SmartDataCard'

interface ChatListProps {
  messages: UIMessage[]
  isLoading?: boolean
}

export function ChatList({ messages, isLoading }: ChatListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Empty state when no messages
  if (messages.length === 0) {
    return (
      <section ref={scrollRef} role="status" aria-label="Waiting for messages" className="flex-1 overflow-y-auto p-6 lg:p-12 flex items-center justify-center">
        <div className="text-center max-w-md">
          {/* Agent Avatar */}
          <div className="mx-auto mb-6 relative group">
            <div className="absolute inset-0 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity bg-[var(--empty-glow)]"></div>
            <div className="relative">
                 <AgentAvatar size="lg" />
            </div>
          </div>
          
          {/* Welcome Text */}
          <h2 className="text-xl font-black mb-2 tracking-tight text-[var(--empty-title)]">
            NEURAL LINK ESTABLISHED
          </h2>
          <p className="text-sm mb-8 font-medium leading-relaxed text-[var(--empty-text)]">
            System ready. Initialization complete.<br/>
            Waiting for direct command input...
          </p>
          
          {/* Status Indicator */}
          <div
            className="inline-flex items-center gap-3 rounded-lg border px-4 py-2 shadow-sm transition-all hover:scale-105 backdrop-blur-sm bg-[var(--empty-indicator-bg)] border-[var(--empty-indicator-border)]"
            style={{ boxShadow: 'var(--empty-indicator-shadow)' }}
          >
            <div className="h-2 w-2 rounded-full animate-pulse bg-[var(--empty-dot)]" style={{ boxShadow: `0 0 8px var(--empty-dot-glow)` }}></div>
            <span className="font-mono text-[10px] font-bold uppercase text-[var(--empty-label-text)]">
                Awaiting Orders
            </span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={scrollRef} role="log" aria-label="Chat messages" className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-6 scroll-smooth custom-scrollbar">
      {messages.map((m) => {
        const isAssistant = m.role === 'assistant';
        
        return (
          <div key={m.id} className={cn("group mx-auto flex max-w-5xl items-start gap-4", !isAssistant && "flex-row-reverse")}>
            
            {/* Avatar Column */}
            <div className="flex flex-col items-center flex-shrink-0 mt-1">
              {isAssistant ? (
                <AgentMessageAvatar />
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
                    timestamp={(m as any).createdAt?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}  
                />
            </div>
          </div>
        )
      })}
      
      {isLoading && (
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

      {/* Spacer */}
      <div className="h-4" />
    </section>
  )
}

