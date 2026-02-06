"use client"

import React, { useRef } from 'react'
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
    <footer className="relative p-6 lg:p-10 flex-shrink-0">
      <div className="relative z-20 mx-auto max-w-4xl">
        <form 
          onSubmit={handleSubmit}
          className="flex items-center rounded-[2rem] border-2 border-blue-100 bg-white/90 p-2 shadow-[0_0_40px_rgba(59,130,246,0.1)] backdrop-blur-xl transition-all duration-300 focus-within:scale-[1.01] focus-within:border-blue-400 focus-within:shadow-[0_0_40px_rgba(59,130,246,0.2)]"
        >
          <button type="button" className="rounded-2xl p-4 text-slate-400 transition-all hover:bg-blue-50 hover:text-blue-500">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
          </button>

          <div className="mx-2 h-8 w-[1px] bg-slate-200"></div>

          <input 
            type="text" 
            placeholder="Enter tactical command..." 
            value={input}
            onChange={handleInputChange}
            disabled={isLoading}
            ref={inputRef}
            className="flex-1 bg-transparent px-4 text-sm font-bold tracking-wide text-slate-700 outline-none placeholder:text-slate-300" 
          />

          <button 
             type="submit"
             disabled={isLoading || !input.trim()}
             className="group rounded-[1.5rem] bg-blue-500 p-4 text-white shadow-lg shadow-blue-200 transition-all hover:bg-blue-600 hover:shadow-blue-400 active:scale-95 disabled:opacity-50 disabled:grayscale"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
          </button>
        </form>

        <div className="mt-3 flex justify-between px-6">
          <span className="font-mono text-[9px] tracking-widest text-slate-400 uppercase">Secure Connection <span className="text-blue-400">TLS_1.3</span></span>
          <span className="font-mono text-[9px] tracking-widest text-slate-400 uppercase">Schale_ID: <span className="text-slate-600">8892-XJ</span></span>
        </div>
      </div>
    </footer>
  )
}

