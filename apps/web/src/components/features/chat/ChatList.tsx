import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'
import { User } from 'lucide-react'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/lib/agent-config'

interface ChatListProps {
  messages: UIMessage[]
}

export function ChatList({ messages }: ChatListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

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
          <div className="mx-auto mb-6">
            <AgentAvatar size="lg" />
          </div>
          
          {/* Welcome Text */}
          <h2 className="text-xl font-black text-slate-700 mb-2">
            Welcome back, {userConfig.name}
          </h2>
          <p className="text-sm text-slate-500 mb-6">
            {agentConfig.name} is ready for your command. Type a message below to start a new tactical operation.
          </p>
          
          {/* Status Indicator */}
          <div className="inline-flex items-center rounded-full border border-blue-100 bg-white/60 px-4 py-2 shadow-sm">
            <div className="mr-2 h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            <span className="font-mono text-[10px] font-bold text-slate-600 uppercase">{agentConfig.title}: <span className="text-emerald-600">Online</span></span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={scrollRef} className="flex-1 overflow-y-auto p-6 lg:p-12 space-y-8 scroll-smooth">
      {messages.map((m) => {
        const isAssistant = m.role === 'assistant';
        
        return (
          <div key={m.id} className={cn("group mx-auto flex max-w-4xl items-start", !isAssistant && "flex-row-reverse")}>
            
            {/* Avatar Column */}
            <div className={cn("flex flex-col items-center", isAssistant ? "mr-6" : "ml-6")}>
              {isAssistant ? (
                <AgentMessageAvatar />
              ) : (
                <div className="relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl border border-indigo-100 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-colors group-hover:border-indigo-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/50 to-transparent"></div>
                  <User className="h-6 w-6 text-indigo-400/80" />
                </div>
              )}
              <div className="my-2 h-full w-[1px] bg-gradient-to-b from-blue-200/50 to-transparent"></div>
            </div>

            {/* Content Column */}
            <div className="flex-1">
              <div className={cn("mb-2 flex items-center justify-between", !isAssistant && "flex-row-reverse")}>
                <span className="rounded bg-slate-100/50 px-2 py-1 text-[10px] font-black tracking-widest text-slate-500 uppercase">
                    {isAssistant ? (
                        <>{agentConfig.name} <span className="text-blue-400">///</span> {agentConfig.title}</>
                    ) : (
                        <>{userConfig.name} <span className="text-indigo-400">///</span> {userConfig.title}</>
                    )}
                </span>
                <span className="font-mono text-[10px] text-slate-300">
                    {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                </span>
              </div>

              <div className={cn(
                  "relative rounded-3xl border p-8 shadow-sm ring-1 backdrop-blur-xl",
                  isAssistant 
                    ? "rounded-tl-none border-white/50 bg-white/70 ring-blue-50" 
                    : "rounded-tr-none border-indigo-100/50 bg-white/80 ring-indigo-50"
              )}>
                {/* Decorative Corners */}
                <div className={cn("absolute top-4 h-3 w-3 rounded-tr-sm border-t-2 border-r-2 opacity-50", isAssistant ? "right-4 border-blue-200" : "left-4 border-indigo-200")}></div>
                <div className={cn("absolute bottom-4 h-3 w-3 rounded-bl-sm border-b-2 border-l-2 opacity-50", isAssistant ? "left-4 border-blue-200" : "right-4 border-indigo-200")}></div>

                <div className="prose prose-sm max-w-none leading-relaxed font-medium text-slate-600 dark:prose-invert">
                  <ReactMarkdown>
                    {m.parts.filter(p => p.type === 'text').map(p => p.text).join('')}
                  </ReactMarkdown>
                </div>
                
                {/* Actions for Assistant Only */}
                {isAssistant && (
                    <div className="mt-6 flex gap-3">
                    <button className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-1.5 text-[10px] font-bold tracking-wider text-blue-600 uppercase transition-colors hover:bg-blue-100">
                        View Requests
                    </button>
                    <button className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[10px] font-bold tracking-wider text-slate-500 uppercase transition-colors hover:bg-slate-50">
                        Dismiss
                    </button>
                    </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </section>
  )
}

