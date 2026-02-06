import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'
import { User } from 'lucide-react'
import { AgentAvatar, AgentMessageAvatar } from '@/components/ui/agent-avatar'
import { agentConfig, userConfig } from '@/lib/agent-config'
import { useTheme } from '@/components/providers/theme-provider'

interface ChatListProps {
  messages: UIMessage[]
}

export function ChatList({ messages }: ChatListProps) {
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
          <div className="mx-auto mb-6">
            <AgentAvatar size="lg" />
          </div>
          
          {/* Welcome Text */}
          <h2 className={cn("text-xl font-black mb-2", isPlana ? "text-slate-200" : "text-slate-700")}>
            Welcome back, {userConfig.name}
          </h2>
          <p className={cn("text-sm mb-6", isPlana ? "text-slate-500" : "text-slate-500")}>
            {agentConfig.name} is ready for your command. Type a message below to start a new tactical operation.
          </p>
          
          {/* Status Indicator */}
          <div className={cn(
              "inline-flex items-center rounded-full border px-4 py-2 shadow-sm transition-colors",
              isPlana ? "bg-[#161b22] border-rose-900/30" : "bg-white/60 border-blue-100"
          )}>
            <div className={cn("mr-2 h-2 w-2 rounded-full animate-pulse", isPlana ? "bg-rose-500 shadow-[0_0_8px_rgba(225,29,72,0.5)]" : "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]")}></div>
            <span className={cn("font-mono text-[10px] font-bold uppercase", isPlana ? "text-slate-400" : "text-slate-600")}>
                {agentConfig.title}: <span className={cn(isPlana ? "text-rose-400" : "text-emerald-600")}>Online</span>
            </span>
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
                <div className={cn(
                    "relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl border shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-colors",
                    isPlana 
                        ? "bg-[#161b22] border-rose-900/20 group-hover:border-rose-700/50" 
                        : "bg-white border-indigo-100 group-hover:border-indigo-300"
                )}>
                  <div className={cn("absolute inset-0 bg-gradient-to-br", isPlana ? "from-rose-900/20 to-transparent" : "from-indigo-50/50 to-transparent")}></div>
                  <User className={cn("h-6 w-6", isPlana ? "text-rose-400/80" : "text-indigo-400/80")} />
                </div>
              )}
              <div className={cn(
                  "my-2 h-full w-[1px] bg-gradient-to-b",
                  isPlana ? "from-rose-900/40 to-transparent" : "from-blue-200/50 to-transparent"
              )}></div>
            </div>

            {/* Content Column */}
            <div className="flex-1">
              <div className={cn("mb-2 flex items-center justify-between", !isAssistant && "flex-row-reverse")}>
                <span className={cn(
                    "rounded px-2 py-1 text-[10px] font-black tracking-widest uppercase",
                    isPlana ? "bg-rose-900/20 text-slate-400" : "bg-slate-100/50 text-slate-500"
                )}>
                    {isAssistant ? (
                        <>{agentConfig.name} <span className={cn(isPlana ? "text-rose-500" : "text-blue-400")}>///</span> {agentConfig.title}</>
                    ) : (
                        <>{userConfig.name} <span className={cn(isPlana ? "text-rose-500" : "text-indigo-400")}>///</span> {userConfig.title}</>
                    )}
                </span>
                <span className={cn("font-mono text-[10px]", isPlana ? "text-slate-600" : "text-slate-300")}>
                    {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                </span>
              </div>

              <div className={cn(
                  "relative rounded-3xl border p-8 shadow-sm ring-1 backdrop-blur-xl",
                  isAssistant 
                    ? (isPlana 
                        ? "rounded-tl-none border-rose-900/20 bg-[#161b22]/70 ring-rose-900/10" 
                        : "rounded-tl-none border-white/50 bg-white/70 ring-blue-50")
                    : (isPlana 
                        ? "rounded-tr-none border-slate-700 bg-[#0d1117]/80 ring-slate-800" 
                        : "rounded-tr-none border-indigo-100/50 bg-white/80 ring-indigo-50")
              )}>
                {/* Decorative Corners */}
                <div className={cn(
                    "absolute top-4 h-3 w-3 rounded-tr-sm border-t-2 border-r-2 opacity-50", 
                    isAssistant 
                        ? (isPlana ? "right-4 border-rose-800/40" : "right-4 border-blue-200")
                        : (isPlana ? "left-4 border-slate-600" : "left-4 border-indigo-200")
                )}></div>
                <div className={cn(
                    "absolute bottom-4 h-3 w-3 rounded-bl-sm border-b-2 border-l-2 opacity-50", 
                    isAssistant 
                        ? (isPlana ? "left-4 border-rose-800/40" : "left-4 border-blue-200")
                        : (isPlana ? "right-4 border-slate-600" : "right-4 border-indigo-200")
                )}></div>

                <div className={cn("prose prose-sm max-w-none leading-relaxed font-medium transition-colors", isPlana ? "prose-invert text-slate-300" : "text-slate-600")}>
                  <ReactMarkdown>
                    {m.parts.filter(p => p.type === 'text').map(p => p.text).join('')}
                  </ReactMarkdown>
                </div>
                
                {/* Actions for Assistant Only */}
                {isAssistant && (
                    <div className="mt-6 flex gap-3">
                    <button className={cn(
                        "rounded-lg border px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase transition-colors",
                        isPlana 
                            ? "border-rose-900/40 bg-rose-900/20 text-rose-400 hover:bg-rose-900/40" 
                            : "border-blue-100 bg-blue-50 text-blue-600 hover:bg-blue-100"
                    )}>
                        View Requests
                    </button>
                    <button className={cn(
                        "rounded-lg border px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase transition-colors",
                        isPlana 
                            ? "border-rose-900/20 bg-[#0d1117] text-slate-500 hover:bg-rose-900/10" 
                            : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
                    )}>
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

