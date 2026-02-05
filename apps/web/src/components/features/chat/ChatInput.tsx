"use client"

import React, { useRef } from 'react'
import { Send, Paperclip } from 'lucide-react'
import { ChatRequestOptions } from 'ai'

interface ChatInputProps {
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>, chatRequestOptions?: ChatRequestOptions | undefined) => void
  isLoading: boolean
}

export function ChatInput({ input, handleInputChange, handleSubmit, isLoading }: ChatInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <footer className="p-6 bg-transparent">
      <div className="max-w-4xl mx-auto relative">
        <div className="absolute -top-4 -left-4 w-8 h-8 border-t-2 border-l-2 border-blue-200 rounded-tl-xl pointer-events-none"></div>
        <div className="absolute -top-4 -right-4 w-8 h-8 border-t-2 border-r-2 border-blue-200 rounded-tr-xl pointer-events-none"></div>
        
        <form 
          onSubmit={handleSubmit}
          className="bg-white border-2 border-blue-100 rounded-[2rem] p-2 flex items-center shadow-2xl shadow-blue-100/50 focus-within:border-blue-400 transition-all backdrop-blur-lg"
        >
          <button type="button" className="p-3 text-slate-300 hover:text-blue-500 transition-colors">
            <Paperclip className="h-6 w-6" />
          </button>
          
          <input 
            ref={inputRef}
            type="text" 
            value={input}
            onChange={handleInputChange}
            disabled={isLoading}
            placeholder="Designate next directive..." 
            className="flex-1 bg-transparent px-4 outline-none text-sm font-bold text-slate-700 placeholder:text-slate-300 disabled:opacity-50" 
          />
          
          <button 
            type="submit"
            disabled={isLoading || !input.trim()} 
            className="bg-blue-500 p-3 rounded-[1.5rem] text-white shadow-lg shadow-blue-200 hover:bg-blue-600 hover:scale-105 transition-all disabled:opacity-50 disabled:grayscale disabled:hover:scale-100"
          >
            <Send className="h-5 w-5" />
          </button>
        </form>
        
        <div className="mt-4 flex justify-between px-6">
            <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">
              Thread_ID: <span className="text-blue-400">SC-2026-X1</span>
            </p>
            <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">
              Encryption: <span className="text-green-500">AES-256_ACTIVE</span>
            </p>
        </div>
      </div>
    </footer>
  )
}

