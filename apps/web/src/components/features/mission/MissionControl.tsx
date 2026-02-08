"use client"

import React, { useState } from 'react'
import { ChatList } from "@/components/features/chat/ChatList"
import { ChatInput } from "@/components/features/chat/ChatInput"
import { ChatSidebar } from "@/components/features/chat/ChatSidebar"
import { OperationalHUD } from "@/components/features/chat/OperationalHUD"
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

  // Map AI status to our HUD status types
  const hudStatus = status === 'ready' ? 'ready' : status === 'error' ? 'error' : status === 'streaming' ? 'streaming' : 'submitted' 

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
          <button onClick={endMission} aria-label="Return to dashboard" className="p-2 rounded-full shadow-md bg-[var(--mission-ctrl-back-bg)] text-[var(--mission-ctrl-back-text)]">
            <ArrowLeft className="w-5 h-5" />
          </button>
      </div>

      {/* Main Chat Content */}
      <div className="flex-1 flex flex-col relative z-10 w-full max-w-full backdrop-blur-sm bg-[var(--mission-ctrl-bg)]">
        
        {/* Superior Operational HUD */}
        <OperationalHUD 
            status={hudStatus} 
            title={activeMissionId ? `MISSION: ${activeMissionId.toUpperCase()}` : 'NEW_OPERATION'} 
            onBack={endMission}
        />

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
