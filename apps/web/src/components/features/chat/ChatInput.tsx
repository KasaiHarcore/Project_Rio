"use client"

import React, { useRef, useState, useEffect } from 'react'
import { ChatRequestOptions } from 'ai'
import { cn } from '@/lib/utils'
import { Textarea } from '@/components/ui/textarea'
import { Plus, ArrowRight, MessageSquare, Database, Sparkles, Server, X } from 'lucide-react'
import { useUIStore, AgentMode } from '@/store/ui-store'

const ALL_AGENT_MODES: { id: AgentMode; label: string; description: string; icon: React.ElementType }[] = [
  { id: 'chat', label: 'Chat', description: 'General conversation', icon: MessageSquare },
  { id: 'rag',  label: 'RAG',  description: 'Document retrieval',  icon: Database },
  { id: 'web',  label: 'Web',  description: 'Internet search',     icon: Sparkles },
  { id: 'sql',  label: 'SQL',  description: 'Database queries',    icon: Server },
]

interface ChatInputProps {
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>, chatRequestOptions?: ChatRequestOptions | undefined) => void
  isLoading: boolean
}

export function ChatInput({ input, handleInputChange, handleSubmit, isLoading }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const agentMode = useUIStore((s) => s.agentMode)
  const setAgentMode = useUIStore((s) => s.setAgentMode)
  const userRole = useUIStore((s) => s.userRole)

  // Only show SQL mode for admin users
  const AGENT_MODES = userRole === 'admin'
    ? ALL_AGENT_MODES
    : ALL_AGENT_MODES.filter((m) => m.id !== 'sql')

  const activeMode = AGENT_MODES.find((m) => m.id === agentMode) ?? AGENT_MODES[0]

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

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
          className="flex items-center rounded-[2rem] border-2 p-2 backdrop-blur-xl transition-all duration-300 focus-within:scale-[1.005] bg-[var(--chat-input-bg)] border-[var(--chat-input-border)] shadow-[0_0_40px_var(--chat-input-glow)] focus-within:border-[var(--chat-input-focus-border)] focus-within:shadow-[0_0_40px_var(--chat-input-glow-focus)]"
        >
          {/* Plus / Mode Selector Button */}
          <div className="relative flex-shrink-0" ref={menuRef}>
            <button
              type="button"
              aria-label="Select mode"
              onClick={() => setMenuOpen((o) => !o)}
              className={cn(
                "rounded-2xl p-4 transition-all",
                menuOpen
                  ? "bg-[var(--chat-input-attach-hover)] text-[var(--chat-input-attach-hover-text)] rotate-45"
                  : "text-[var(--chat-input-attach-text)] hover:bg-[var(--chat-input-attach-hover)] hover:text-[var(--chat-input-attach-hover-text)]"
              )}
            >
              <Plus className="h-5 w-5 transition-transform duration-200" />
            </button>

            {/* Mode Popover */}
            {menuOpen && (
              <div className="absolute bottom-full left-0 mb-3 w-52 rounded-2xl border-2 p-2 backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 duration-200 bg-[var(--chat-input-bg)] border-[var(--chat-input-border)] shadow-[0_8px_40px_rgba(0,0,0,0.25)]">
                <p className="px-3 pt-1.5 pb-2 text-[10px] font-bold uppercase tracking-widest text-[var(--chat-input-placeholder)]">
                  Agent Mode
                </p>
                {AGENT_MODES.map((mode) => {
                  const isActive = mode.id === agentMode
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => { setAgentMode(mode.id); setMenuOpen(false) }}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all duration-150",
                        isActive
                          ? "bg-[var(--chat-input-send-bg)] text-white shadow-sm"
                          : "text-[var(--chat-input-text)] hover:bg-[var(--chat-input-attach-hover)]"
                      )}
                    >
                      <mode.icon className="h-4 w-4 flex-shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-xs font-bold tracking-wide">{mode.label}</span>
                        <span className={cn("block text-[10px]", isActive ? "text-white/60" : "text-[var(--chat-input-placeholder)]")}>
                          {mode.description}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="mx-2 self-stretch w-[1px] my-2 bg-[var(--chat-input-divider)]"></div>

          {/* Active mode badge */}
          <div className="flex items-center gap-1.5 rounded-lg px-2 py-1 mr-1 flex-shrink-0 bg-[var(--chat-input-attach-hover)]">
            <activeMode.icon className="h-3.5 w-3.5 text-[var(--chat-input-attach-hover-text)]" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--chat-input-attach-hover-text)]">
              {activeMode.label}
            </span>
          </div>

          <Textarea
            placeholder="Type a message..."
            aria-label="Chat message input"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            ref={textareaRef}
            maxHeight={88}
            className="flex-1 min-w-0 px-4 py-4 text-[var(--chat-input-text)] placeholder:text-[var(--chat-input-placeholder)]"
          />

          <button 
             type="submit"
             disabled={isLoading || !input.trim()}
             aria-label="Send message"
             className="group rounded-[1.5rem] p-4 ml-2 text-white shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:grayscale flex-shrink-0 bg-[var(--chat-input-send-bg)] shadow-[var(--chat-input-send-shadow)] hover:bg-[var(--chat-input-send-hover)] hover:shadow-[var(--chat-input-send-hover-shadow)]"
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

