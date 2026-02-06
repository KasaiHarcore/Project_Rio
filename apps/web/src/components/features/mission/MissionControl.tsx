"use client"

import React, { useState, useEffect } from 'react'
import { ChatHeader } from "@/components/features/chat/ChatHeader"
import { ChatList } from "@/components/features/chat/ChatList"
import { ChatInput } from "@/components/features/chat/ChatInput"
import { ChatSidebar } from "@/components/features/chat/ChatSidebar"
import { useChat } from '@ai-sdk/react'
import type { ChatRequestOptions, UIMessage } from 'ai'
import { useUIStore } from '@/store/ui-store'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

export function MissionControl() {
  const [input, setInput] = useState('')
  const chatKey = useUIStore((state) => state.chatKey)
  const activeMissionId = useUIStore((state) => state.activeMissionId)
  const endMission = useUIStore((state) => state.endMission)
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  // Use mission ID for chat persistence if available
  const { messages, sendMessage, status } = useChat<UIMessage>({ 
    id: activeMissionId ? `mission-${activeMissionId}` : `chat-${chatKey}` 
  })

  const isLoading = status === 'submitted' || status === 'streaming'

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>, chatRequestOptions?: ChatRequestOptions) => {
    e.preventDefault()
    if (!input.trim()) return
    
    sendMessage({ text: input }, chatRequestOptions)
    setInput('')
  }
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }

  return (
    <div className="flex flex-1 overflow-hidden h-full relative">
      {/* Return Button (absolute positioned for specific layout integration) */}
      <div className="absolute top-4 left-4 z-50 lg:hidden">
          <button onClick={endMission} className={cn("p-2 rounded-full shadow-md", isPlana ? "bg-[#161b22] text-slate-200" : "bg-white text-slate-600")}>
            <ArrowLeft className="w-5 h-5" />
          </button>
      </div>

      {/* Main Chat Content */}
      <div className={cn("flex-1 flex flex-col relative z-10 w-full max-w-full backdrop-blur-sm", isPlana ? "bg-[#0d1117]/30" : "bg-white/30")}>
        <div className={cn("flex items-center px-6 py-2 border-b backdrop-blur-md", isPlana ? "bg-[#161b22]/50 border-rose-900/20" : "bg-white/50 border-blue-100")}>
            <button 
                onClick={endMission}
                className={cn("mr-4 p-2 rounded-lg transition-colors group", isPlana ? "hover:bg-rose-900/20" : "hover:bg-slate-100")}
                title="Return to Office"
            >
                <ArrowLeft className={cn("w-5 h-5 group-hover:text-blue-500", isPlana ? "text-slate-500 group-hover:text-rose-500" : "text-slate-400")} />
            </button>
            <div>
                 <h2 className={cn("text-sm font-bold", isPlana ? "text-slate-200" : "text-slate-700")}>MISSION: {activeMissionId ? activeMissionId.toUpperCase() : 'NEW_OPERATION'}</h2>
                 <p className={cn("text-[10px] font-mono flex items-center gap-1", isPlana ? "text-rose-500" : "text-emerald-500")}>
                    <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", isPlana ? "bg-rose-500" : "bg-emerald-500")}></span>
                    LINK_ESTABLISHED
                 </p>
            </div>
        </div>

        <ChatList 
             messages={messages} 
             isLoading={isLoading} 
        />
        
        <ChatInput 
            input={input} 
            handleInputChange={handleInputChange} 
            handleSubmit={handleSubmit} 
            isLoading={isLoading} 
        />
      </div>

      {/* Right Sidebar (Chat details) */}
      <ChatSidebar /> 
    </div>
  )
}
