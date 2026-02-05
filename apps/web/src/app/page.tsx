"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ChatHeader } from "@/components/features/chat/ChatHeader"
import { ChatList } from "@/components/features/chat/ChatList"
import { ChatInput } from "@/components/features/chat/ChatInput"
import { ChatSidebar } from "@/components/features/chat/ChatSidebar"
import { SplashScreen } from "@/components/layout/splash-screen"
import { AnimatePresence } from "framer-motion"
import { useChat } from '@ai-sdk/react'

export default function Page() {
  const [showSplash, setShowSplash] = useState(true)
  const [input, setInput] = useState('')
  
  const { messages, sendMessage, status } = useChat({
     api: '/api/chat',
     initialMessages: [
         {
             id: 'welcome',
             role: 'assistant',
             content: "System Check: **OK**. Neural link stable. Sensei, Aris is ready for the next level! How can I assist with your study plan today?"
         }
     ]
  })

  // Start with explicit loading state derived from status
  const isLoading = status === 'submitted' || status === 'streaming'

  const handleSubmit = (e: React.FormEvent, chatRequestOptions?: any) => {
    e.preventDefault()
    if (!input.trim()) return
    
    // Send message using the new API signature
    sendMessage({ role: 'user', content: input })
    setInput('')
  }
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }

  return (
    <>
      <AnimatePresence>
        {showSplash && (
          <SplashScreen onComplete={() => setShowSplash(false)} />
        )}
      </AnimatePresence>
      
      {!showSplash && (
        <DashboardLayout>
          <div className="flex flex-1 overflow-hidden">
            {/* Main Chat Content */}
            <div className="flex-1 flex flex-col relative bg-white/30 backdrop-blur-sm z-10 w-full max-w-full">
              <ChatHeader />
              <ChatList messages={messages} />
              <ChatInput 
                input={input} 
                handleInputChange={handleInputChange} 
                handleSubmit={handleSubmit}
                isLoading={isLoading}
              />
            </div>

            {/* Right Sidebar */}
            <ChatSidebar />
          </div>
        </DashboardLayout>
      )}
    </>
  )
}

