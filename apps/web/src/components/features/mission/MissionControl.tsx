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

export function MissionControl() {
  const [input, setInput] = useState('')
  const chatKey = useUIStore((state) => state.chatKey)
  const activeMissionId = useUIStore((state) => state.activeMissionId)
  const endMission = useUIStore((state) => state.endMission)

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
          <button onClick={endMission} className="p-2 bg-white rounded-full shadow-md">
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
      </div>

      {/* Main Chat Content */}
      <div className="flex-1 flex flex-col relative z-10 w-full max-w-full bg-white/30 backdrop-blur-sm">
        <div className="flex items-center px-6 py-2 border-b border-blue-100 bg-white/50 backdrop-blur-md">
            <button 
                onClick={endMission}
                className="mr-4 p-2 hover:bg-slate-100 rounded-lg transition-colors group"
                title="Return to Office"
            >
                <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-blue-500" />
            </button>
            <div>
                 <h2 className="text-sm font-bold text-slate-700">MISSION: {activeMissionId ? activeMissionId.toUpperCase() : 'NEW_OPERATION'}</h2>
                 <p className="text-[10px] text-emerald-500 font-mono flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
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
