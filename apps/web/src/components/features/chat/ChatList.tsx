import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import { cn } from '@/lib/utils'
import { User } from 'lucide-react'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/lib/agent-config'
import { useTheme } from '@/components/providers/theme-provider'
import { SmartDataCard } from './SmartDataCard'

interface ChatListProps {
  messages: UIMessage[]
  isLoading?: boolean
}

export function ChatList({ messages, isLoading }: ChatListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Empty state when no messages
  if (messages.length === 0) {
    return (
      <section ref={scrollRef} className="flex-1 overflow-y-auto p-6 lg:p-12 flex items-center justify-center">
        <div className="text-center max-w-md">
          {/* Agent Avatar */}
          <div className="mx-auto mb-6 relative group">
            <div className={cn("absolute inset-0 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity", isPlana ? "bg-rose-500" : "bg-blue-500")}></div>
            <div className="relative">
                 <AgentAvatar size="lg" />
            </div>
          </div>
          
          {/* Welcome Text */}
          <h2 className={cn("text-xl font-black mb-2 tracking-tight", isPlana ? "text-slate-200" : "text-slate-700")}>
            NEURAL LINK ESTABLISHED
          </h2>
          <p className={cn("text-sm mb-8 font-medium leading-relaxed", isPlana ? "text-slate-500" : "text-slate-500")}>
            System ready. Initialization complete.<br/>
            Waiting for direct command input...
          </p>
          
          {/* Status Indicator */}
          <div className={cn(
              "inline-flex items-center gap-3 rounded-lg border px-4 py-2 shadow-sm transition-all hover:scale-105 backdrop-blur-sm",
              isPlana ? "bg-[#161b22]/50 border-rose-900/30 shadow-[0_4px_20px_rgba(225,29,72,0.1)]" : "bg-white/60 border-blue-100 shadow-[0_4px_20px_rgba(37,99,235,0.1)]"
          )}>
            <div className={cn("h-2 w-2 rounded-full animate-pulse", isPlana ? "bg-rose-500 shadow-[0_0_8px_rgba(225,29,72,0.8)]" : "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]")}></div>
            <span className={cn("font-mono text-[10px] font-bold uppercase", isPlana ? "text-slate-400" : "text-slate-600")}>
                Awaiting Orders
            </span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={scrollRef} className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-6 scroll-smooth custom-scrollbar">
      {messages.map((m) => {
        const isAssistant = m.role === 'assistant';
        
        return (
          <div key={m.id} className={cn("group mx-auto flex max-w-5xl items-start gap-4", !isAssistant && "flex-row-reverse")}>
            
            {/* Avatar Column */}
            <div className={cn("flex flex-col items-center flex-shrink-0 mt-1")}>
              {isAssistant ? (
                <AgentMessageAvatar />
              ) : (
                <div className={cn(
                    "relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-colors",
                    isPlana 
                        ? "bg-[#161b22] border-rose-900/30" 
                        : "bg-white border-blue-100"
                )}>
                  <User className={cn("h-5 w-5", isPlana ? "text-rose-400" : "text-slate-400")} />
                </div>
              )}
            </div>

            {/* Content Column (Smart Card) */}
            <div className="flex-1 min-w-0 max-w-[85%]">
                <SmartDataCard 
                    role={m.role as any} 
                    content={m.content} 
                    isPlana={isPlana}
                    timestamp={m.createdAt?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}  
                />
            </div>
          </div>
        )
      })}
      
      {isLoading && (
          <div className="mx-auto flex max-w-5xl items-center gap-4 animate-pulse opacity-50">
               <div className="h-10 w-10 rounded-full bg-gray-200/20" />
               <div className="h-24 w-full flex-1 rounded-xl bg-gray-200/10" />
          </div>
      )}

      {/* Spacer */}
      <div className="h-4" />
    </section>
  )
}

