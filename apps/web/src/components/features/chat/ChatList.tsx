import React, { useEffect, useRef } from 'react'
import { UIMessage } from 'ai'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'

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

  if (messages.length === 0) {
    return (
      <section className="flex-1 overflow-y-auto p-8 flex flex-col items-center justify-center text-center opacity-50">
         <div className="w-16 h-16 bg-blue-100/50 rounded-2xl mb-4 flex items-center justify-center animate-pulse">
            <span className="text-2xl">🤖</span>
         </div>
         <h3 className="text-sm font-bold text-slate-500">System Ready</h3>
         <p className="text-xs text-slate-400 mt-1">Awaiting directive...</p>
      </section>
    )
  }

  return (
    <section ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
      {messages.map((m) => (
        <div key={m.id} className={cn("flex items-start space-x-5 max-w-4xl group", m.role === 'user' ? "flex-row-reverse space-x-reverse ml-auto" : "")}>
          
          {/* Avatar */}
          <div className="flex flex-col items-center flex-shrink-0">
              <div className={cn(
                "w-10 h-10 rounded-2xl flex items-center justify-center border-2 shadow-xl mt-6 relative overflow-hidden transition-colors",
                m.role === 'assistant' 
                    ? "bg-white border-blue-100 shadow-blue-100/50" 
                    : "bg-blue-500 border-blue-600 shadow-blue-500/30"
              )}>
                  {m.role === 'assistant' ? (
                     <>
                        <div className="absolute inset-0 bg-blue-50 opacity-40"></div>
                        <span className="text-blue-600 font-black text-[10px] relative">AI</span>
                     </>
                  ) : (
                     <span className="text-white font-black text-[10px]">YOU</span>
                  )}
              </div>
              {m.role === 'assistant' && (
                 <div className="h-full w-0.5 bg-gradient-to-b from-blue-100 to-transparent mt-2"></div>
              )}
          </div>
      
          {/* Content */}
          <div className={cn("flex flex-col flex-1 max-w-[85%]", m.role === 'user' ? "items-end" : "items-start")}>
            <div className={cn("flex items-center space-x-3 mb-2 ml-1", m.role === 'user' ? "flex-row-reverse space-x-reverse" : "")}>
              <span className="text-[10px] font-black text-slate-800 uppercase tracking-widest">
                {m.role === 'assistant' ? 'Aris Neural Core' : 'Sensei'}
              </span>
              <span className="text-[9px] font-mono text-slate-400">
                {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </span>
            </div>
      
            <div className={cn(
                "backdrop-blur-md border p-6 rounded-[2rem] shadow-sm relative transition-all hover:shadow-md text-sm leading-relaxed",
                m.role === 'assistant' 
                    ? "bg-white/80 border-blue-50 rounded-tl-none hover:border-blue-200 text-slate-600" 
                    : "bg-blue-500/90 border-blue-500 rounded-tr-none text-white"
            )}>
              {/* Triangle Tail */}
              <div className={cn(
                 "absolute top-0 w-0 h-0 border-t-[10px] border-t-white",
                 m.role === 'assistant' 
                    ? "border-t-[10px] border-t-transparent border-l-[10px] border-l-transparent border-r-[10px] -left-2 top-0 border-r-white/0" // Complex CSS shapes are hard, using simple absolute positioning
                    : "hidden"
              )}></div>
              
              <div className="prose prose-sm prose-blue max-w-none dark:prose-invert">
                 <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
      
              {m.role === 'assistant' && (
                <div className="mt-3 flex space-x-2">
                    <span className="px-2 py-1 bg-blue-50 text-[9px] font-bold text-blue-500 rounded-md border border-blue-100 uppercase tracking-widest">Processing</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </section>
  )
}

