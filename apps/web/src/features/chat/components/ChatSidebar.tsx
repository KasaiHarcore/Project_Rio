"use client"

import React, { useMemo } from 'react'
import { cn } from '@/shared/lib/utils'
import { useSidebarStore, type SidebarTab } from '@/features/chat/store'
import { useUIStore } from '@/shared/store/ui-store'
import { CHARACTERS } from '@/features/rio/types'
import {
  Bot, FolderKanban, BrainCircuit,
  Download, Hash, Zap, Clock,
} from 'lucide-react'
import type { UIMessage } from 'ai'

import { AgentsTab } from './sidebar/AgentsTab'
import { WorkspaceTab } from './sidebar/WorkspaceTab'
import { MemoryTab } from './sidebar/MemoryTab'
import { NotePopup } from '@/features/notes/components/NotePopup'

/* ─── Types ──────────────────────────────────────────────────────── */

type HudStatus = 'ready' | 'streaming' | 'submitted' | 'error'

interface ChatSidebarProps {
  messages: UIMessage[]
  status: HudStatus
  threadId: string | null
  treeView?: boolean
  onToggleTreeView?: () => void
}

/* ─── Tab definitions ────────────────────────────────────────────── */

const TABS: { id: SidebarTab; label: string; icon: React.ComponentType<Record<string, unknown>> }[] = [
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'workspace', label: 'Workspace', icon: FolderKanban },
  { id: 'memory', label: 'Memory', icon: BrainCircuit },
]

/* ─── Helpers ────────────────────────────────────────────────────── */

function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4)
}

function formatDuration(ms: number): string {
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'Just started'
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ${mins % 60}m`
}

/* ═══════════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════════ */

export function ChatSidebar({ messages, status, threadId, treeView, onToggleTreeView }: ChatSidebarProps) {
  const activeTab = useSidebarStore((s) => s.activeTab)
  const setActiveTab = useSidebarStore((s) => s.setActiveTab)
  const character = CHARACTERS[0]

  /* ── Badge counts for tab indicators ── */
  const logicCount = useSidebarStore((s) => s.logicEntries.length)
  const notesCount = useSidebarStore((s) => s.stickyNotes.length)
  const filesCount = useSidebarStore((s) => s.workspaceFiles.length)
  const refsCount = useSidebarStore((s) => s.searchReferences.length)
  const memoryCount = useSidebarStore((s) => s.memoryEntries.length + s.persistedMemories.length)

  const tabBadges: Record<SidebarTab, number> = {
    agents: logicCount + notesCount,
    workspace: filesCount + refsCount,
    memory: memoryCount,
  }

  /* ── Derived session stats for footer ── */
  const stats = useMemo(() => {
    const allText = messages.map((m) =>
      m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || (m as any).content || ''
    ).join('')

    const tokens = estimateTokens(allText)

    const firstMsg = messages[0]
    const sessionStart = firstMsg ? new Date((firstMsg as any).createdAt ?? Date.now()).getTime() : Date.now()
    const duration = Date.now() - sessionStart

    return { msgCount: messages.length, tokens, duration }
  }, [messages])

  const chatSidebarOpen = useUIStore((s) => s.chatSidebarOpen)

  if (!chatSidebarOpen) return null

  return (
    <>
      <aside className="relative z-20 hidden w-80 flex-col border-l backdrop-blur-xl 2xl:flex flex-shrink-0 transition-colors overflow-hidden bg-[var(--chat-sidebar-bg)] border-[var(--chat-sidebar-border)]">

        {/* ───── Tab bar ───── */}
        <div className="flex items-center gap-1 border-b px-3 py-2 border-[var(--chat-sidebar-section-border)]">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            const badge = tabBadges[tab.id]
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all",
                  "text-[9px] font-bold uppercase tracking-wider",
                  isActive
                    ? "text-[var(--chat-sidebar-stat-text)] bg-[var(--chat-sidebar-stat-text)]/10"
                    : "text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-value)] hover:bg-[var(--chat-sidebar-artifact-bg)]"
                )}
              >
                <tab.icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
                {badge > 0 && (
                  <span className={cn(
                    "min-w-[14px] h-[14px] rounded-full px-1 flex items-center justify-center text-[7px] font-black",
                    isActive
                      ? "bg-[var(--chat-sidebar-stat-text)]/20 text-[var(--chat-sidebar-stat-text)]"
                      : "bg-[var(--chat-sidebar-stat-label)]/20 text-[var(--chat-sidebar-stat-label)]"
                  )}>
                    {badge}
                  </span>
                )}
              </button>
            )
          })}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Export button */}
          {messages.length > 0 && (
            <button
              onClick={() => {
                const md = messages.map(m => {
                  const content = m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || (m as any).content || ''
                  return `**${m.role === 'user' ? 'You' : character.name}:**\n${content}`
                }).join('\n\n---\n\n')
                const blob = new Blob([md], { type: 'text/markdown' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `chat-${threadId?.substring(0, 8) || 'new'}-${new Date().toISOString().split('T')[0]}.md`
                a.click()
                URL.revokeObjectURL(url)
              }}
              className="p-1.5 rounded-lg transition-colors text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)] hover:bg-[var(--chat-sidebar-artifact-bg)]"
              title="Export chat"
            >
              <Download className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* ───── Tab content ───── */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {activeTab === 'agents' && <AgentsTab treeView={treeView} onToggleTreeView={onToggleTreeView} />}
          {activeTab === 'workspace' && <WorkspaceTab />}
          {activeTab === 'memory' && <MemoryTab threadId={threadId} />}
        </div>

        {/* ───── Compact session footer ───── */}
        {messages.length > 0 && (
          <div className="flex items-center justify-between border-t px-4 py-2 border-[var(--chat-sidebar-section-border)]">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <Hash className="h-2.5 w-2.5 text-[var(--chat-sidebar-stat-label)]" />
                <span className="text-[8px] font-bold text-[var(--chat-sidebar-stat-label)]">{stats.msgCount}</span>
              </div>
              <div className="flex items-center gap-1">
                <Zap className="h-2.5 w-2.5 text-[var(--chat-sidebar-stat-label)]" />
                <span className="text-[8px] font-bold text-[var(--chat-sidebar-stat-label)]">
                  {stats.tokens > 1000 ? `${(stats.tokens / 1000).toFixed(1)}k` : stats.tokens}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-2.5 w-2.5 text-[var(--chat-sidebar-stat-label)]" />
                <span className="text-[8px] font-bold text-[var(--chat-sidebar-stat-label)]">{formatDuration(stats.duration)}</span>
              </div>
            </div>
            {threadId && (
              <span className="text-[7px] font-mono text-[var(--chat-sidebar-stat-label)]/50 truncate max-w-[80px]">
                {threadId.substring(0, 8)}
              </span>
            )}
          </div>
        )}
      </aside>

      {/* Note Popup — rendered here so it's above the sidebar */}
      <NotePopup />
    </>
  )
}
