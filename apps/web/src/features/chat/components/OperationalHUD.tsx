import React, { useState, useRef, useEffect, useMemo } from 'react'
import { cn } from '@/shared/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Database, Search, ArrowLeft, PanelRightOpen, PanelRightClose, X } from 'lucide-react'
import { useUIStore } from '@/shared/store/ui-store'
import type { UIMessage } from 'ai'

interface OperationalHUDProps {
  status: 'ready' | 'submitted' | 'streaming' | 'error'
  title?: string
  onBack?: () => void
  messages?: UIMessage[]
}

// Status messages mapping
const STATUS_MESSAGES: Record<string, string> = {
  streaming: "Processing your query...",
  ready: "Analysis complete. Ask if you need clarification.",
  submitted: "Thinking...",
  error: "Connection disrupted. Retrying..."
}

export function OperationalHUD({ status, title = "OPERATIONAL_MODE", onBack, messages = [] }: OperationalHUDProps) {
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)
  const chatSidebarOpen = useUIStore((s) => s.chatSidebarOpen)
  const toggleChatSidebar = useUIStore((s) => s.toggleChatSidebar)

  // Focus input when search opens
  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus()
  }, [searchOpen])

  // Close search on Escape
  useEffect(() => {
    if (!searchOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setSearchOpen(false); setSearchQuery('') }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [searchOpen])

  // Search result count
  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0
    const q = searchQuery.toLowerCase()
    return messages.filter((m) => {
      const text = m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || (m as any).content || ''
      return text.toLowerCase().includes(q)
    }).length
  }, [searchQuery, messages])

  return (
    <div
      className="relative backdrop-blur-md border-b z-20 overflow-hidden transition-all duration-500 bg-[var(--hud-bg)] border-[var(--hud-border)]"
      style={{ boxShadow: 'var(--hud-shadow)' }}
    >
      <div className="flex items-center justify-between px-4 md:px-6 py-3 relative z-10 gap-2">

          {/* Left: Identity Block */}
          <div className="flex items-center gap-3 min-w-0">
              {onBack && (
                <button
                  onClick={onBack}
                  aria-label="Go back"
                  className="p-2 rounded-lg transition-colors group flex-shrink-0 text-[var(--hud-back-text)] hover:bg-[var(--hud-back-hover)] hover:text-[var(--hud-back-hover-text)]"
                >
                  <ArrowLeft size={18} />
                </button>
              )}

              <div className="p-2 rounded-lg border backdrop-blur-sm flex-shrink-0 bg-[var(--hud-icon-bg)] border-[var(--hud-icon-border)]">
                 <Database size={16} className="text-[var(--hud-icon-text)]" />
              </div>
              <div className="flex flex-col min-w-0">
                <h2 className="text-xs font-black tracking-[0.2em] uppercase truncate text-[var(--hud-title-text)]">
                    {title}
                </h2>
                <span className="text-[9px] text-white/70 font-medium tracking-wide">
                  {STATUS_MESSAGES[status] || 'Ready'}
                </span>
              </div>
          </div>

          {/* Right: Search + Sidebar toggle */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {/* Search chat */}
            <AnimatePresence>
              {searchOpen && (
                <motion.div
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 200, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="relative overflow-hidden"
                >
                  <input
                    ref={searchInputRef}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search chat..."
                    className="w-full h-8 pl-3 pr-8 text-xs font-bold rounded-lg border outline-none transition-colors bg-[var(--hud-status-bg)] border-[var(--hud-status-border)] text-[var(--hud-title-text)] placeholder:text-[var(--hud-status-label)]"
                  />
                  {searchQuery && (
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] font-black text-[var(--hud-status-label)]">
                      {matchCount}
                    </span>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            <button
              onClick={() => { setSearchOpen((o) => !o); if (searchOpen) setSearchQuery('') }}
              aria-label={searchOpen ? "Close search" : "Search chat"}
              className={cn(
                "p-2 rounded-lg transition-colors",
                searchOpen
                  ? "text-[var(--hud-back-hover-text)] bg-[var(--hud-back-hover)]"
                  : "text-[var(--hud-back-text)] hover:bg-[var(--hud-back-hover)] hover:text-[var(--hud-back-hover-text)]"
              )}
            >
              {searchOpen ? <X size={16} /> : <Search size={16} />}
            </button>

            {/* Sidebar toggle — hidden on screens where sidebar auto-shows */}
            <button
              onClick={toggleChatSidebar}
              aria-label={chatSidebarOpen ? "Close sidebar" : "Open sidebar"}
              className="p-2 rounded-lg transition-colors text-[var(--hud-back-text)] hover:bg-[var(--hud-back-hover)] hover:text-[var(--hud-back-hover-text)]"
            >
              {chatSidebarOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
          </div>
      </div>

      {/* Progress Line for Processing */}
      {status === 'streaming' && (
          <motion.div
            layoutId="active-line"
            className="absolute bottom-0 left-0 h-[2px] w-full bg-[var(--hud-progress-bar)]"
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.5, ease: "circIn" }}
          />
      )}
    </div>
  )
}
