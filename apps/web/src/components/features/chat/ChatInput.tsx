"use client"

import React, { useRef } from 'react'
import { ChatRequestOptions } from 'ai'
import { cn } from '@/lib/utils'
import { Textarea } from '@/components/ui/textarea'
import { Paperclip, ArrowRight } from 'lucide-react'

interface ChatInputProps {
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>, chatRequestOptions?: ChatRequestOptions | undefined) => void
  isLoading: boolean
}

export function ChatInput({ input, handleInputChange, handleSubmit, isLoading }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && !isLoading) {
        handleSubmit(e as unknown as React.FormEvent<HTMLFormElement>)
      }
    }
  }

  return (
    <footer className="relative p-3 md:p-6 lg:p-10 flex-shrink-0">
      <div className="relative z-20 mx-auto max-w-4xl">
        <form 
          onSubmit={handleSubmit}
          className="flex items-end rounded-[2rem] border-2 p-2 backdrop-blur-xl transition-all duration-300 focus-within:scale-[1.005] bg-[var(--chat-input-bg)] border-[var(--chat-input-border)] shadow-[0_0_40px_var(--chat-input-glow)] focus-within:border-[var(--chat-input-focus-border)] focus-within:shadow-[0_0_40px_var(--chat-input-glow-focus)]"
        >
          <button 
             type="button" 
             aria-label="Attach file"
             className="rounded-2xl p-4 transition-all flex-shrink-0 text-[var(--chat-input-attach-text)] hover:bg-[var(--chat-input-attach-hover)] hover:text-[var(--chat-input-attach-hover-text)]"
          >
            <Paperclip className="h-5 w-5" />
          </button>

          <div className="mx-2 self-stretch w-[1px] my-2 bg-[var(--chat-input-divider)]"></div>

          <Textarea
            placeholder="Type a message..."
            aria-label="Chat message input"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            ref={textareaRef}
            maxHeight={160}
            className="flex-1 px-4 py-3 text-[var(--chat-input-text)] placeholder:text-[var(--chat-input-placeholder)]"
          />

          <button 
             type="submit"
             disabled={isLoading || !input.trim()}
             aria-label="Send message"
             className="group rounded-[1.5rem] p-4 text-white shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:grayscale flex-shrink-0 bg-[var(--chat-input-send-bg)] shadow-[var(--chat-input-send-shadow)] hover:bg-[var(--chat-input-send-hover)] hover:shadow-[var(--chat-input-send-hover-shadow)]"
          >
            <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" strokeWidth={3} />
          </button>
        </form>

        <div className="mt-2 flex justify-center px-6">
          <span className="text-[10px] font-medium text-[var(--chat-input-hint-text)]">
            <kbd className="font-mono text-[9px] px-1 py-0.5 rounded border border-current/20 mr-1">Enter</kbd> to send · <kbd className="font-mono text-[9px] px-1 py-0.5 rounded border border-current/20 mx-1">Shift + Enter</kbd> for new line
          </span>
        </div>
      </div>
    </footer>
  )
}

