"use client"

import React, { Suspense, useState, useEffect, useCallback, useRef } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { MessageSquare, Plus, Search, Loader2, MoreHorizontal, Pencil, Trash2, Star, Pin, Archive, ArchiveRestore, X, Check } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { MissionControl } from "@/features/mission/components/MissionControl"

import { apiListThreads, apiDeleteThread, apiUpdateThread, ThreadSummary } from '@/features/chat/api'
import { useSearchParams, useRouter } from 'next/navigation'

function relativeTime(iso: string): string {
    if (!iso) return ''
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return 'Just now'
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    const diffDay = Math.floor(diffHr / 24)
    if (diffDay === 1) return 'Yesterday'
    if (diffDay < 7) return d.toLocaleDateString('en-US', { weekday: 'short' })
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function OperationView({ initialThreadId }: { initialThreadId?: string } = {}) {
    return (
        <Suspense>
            <OperationContent initialThreadId={initialThreadId} />
        </Suspense>
    )
}

function OperationContent({ initialThreadId }: { initialThreadId?: string }) {
    const router = useRouter()
    const [selectedOpId, setSelectedOpId] = useState<string | null>(initialThreadId ?? null)
    // Separate key that only changes on explicit user navigation (click thread / new),
    // NOT when handleThreadCreated resolves a '__new__' → UUID transition.
    // This prevents React from unmounting MissionControl mid-stream.
    const [missionKey, setMissionKey] = useState(0)
    const [threads, setThreads] = useState<ThreadSummary[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [showArchived, setShowArchived] = useState(false)
    const searchParams = useSearchParams()
    const hasHandledNewParam = useRef(false)

    // ── Context menu state ──────────────────────────────────────────────
    const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
    const [renamingId, setRenamingId] = useState<string | null>(null)
    const [renameValue, setRenameValue] = useState('')
    const menuRef = useRef<HTMLDivElement>(null)
    const renameInputRef = useRef<HTMLInputElement>(null)

    // Handle legacy ?thread= and ?new= query params (redirect to path-based URL)
    useEffect(() => {
        if (hasHandledNewParam.current) return
        const threadParam = searchParams.get('thread')
        const isNew = searchParams.get('new') === 'true'
        if (threadParam) {
            hasHandledNewParam.current = true
            setSelectedOpId(threadParam)
            setMissionKey(k => k + 1)
            router.replace(`/operation/${threadParam}`)
        } else if (isNew) {
            hasHandledNewParam.current = true
            setSelectedOpId('__new__')
            setMissionKey(k => k + 1)
            router.replace('/operation')
        }
    }, [searchParams, router])

    // If mounted with initialThreadId, ensure MissionControl mounts
    useEffect(() => {
        if (initialThreadId) {
            setMissionKey(k => k + 1)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // ── Fetch threads ────────────────────────────────────────────────────
    const fetchThreads = useCallback(async () => {
        try {
            setLoading(true)
            const data = await apiListThreads(50)
            setThreads(data.threads)
        } catch {
            // silently fail – user might not be authenticated yet
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchThreads() }, [fetchThreads])

    // ── New operation → navigate to fresh chat ───────────────────────────
    const handleNewOperation = () => {
        setSelectedOpId('__new__')
        setMissionKey(k => k + 1)
    }

    // When backend creates a new thread, update selectedOpId so subsequent
    // messages continue on the same thread, and refresh the list.
    const handleThreadCreated = useCallback((newThreadId: string) => {
        setSelectedOpId(newThreadId)
        router.replace(`/operation/${newThreadId}`)
        fetchThreads()
    }, [fetchThreads, router])

    // Refresh thread list when a message exchange completes
    const handleMessageComplete = useCallback(() => {
        fetchThreads()
    }, [fetchThreads])

    // Mobile: go back to thread list (deselect, don't leave the page)
    const handleBackToList = useCallback(() => {
        setSelectedOpId(null)
        router.replace('/operation')
    }, [router])

    // ── Close menu on outside click ────────────────────────────────────
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpenId(null)
            }
        }
        if (menuOpenId) {
            document.addEventListener('mousedown', handleClickOutside)
            return () => document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [menuOpenId])

    // ── Focus rename input when it appears ─────────────────────────────
    useEffect(() => {
        if (renamingId && renameInputRef.current) {
            renameInputRef.current.focus()
            renameInputRef.current.select()
        }
    }, [renamingId])

    // ── Thread actions ─────────────────────────────────────────────────
    const handleRenameStart = (op: ThreadSummary) => {
        setRenamingId(op.id)
        setRenameValue(op.title ?? '')
        setMenuOpenId(null)
    }

    const handleRenameConfirm = async (id: string) => {
        const trimmed = renameValue.trim()
        if (!trimmed) { setRenamingId(null); return }
        try {
            await apiUpdateThread(id, { title: trimmed })
            setThreads(prev => prev.map(t => t.id === id ? { ...t, title: trimmed } : t))
        } catch { /* swallow */ }
        setRenamingId(null)
    }

    const handleRenameKeyDown = (e: React.KeyboardEvent, id: string) => {
        if (e.key === 'Enter') handleRenameConfirm(id)
        if (e.key === 'Escape') setRenamingId(null)
    }

    const handleDelete = async (id: string) => {
        setMenuOpenId(null)
        try {
            await apiDeleteThread(id)
            setThreads(prev => prev.filter(t => t.id !== id))
            if (selectedOpId === id) setSelectedOpId(null)
        } catch { /* swallow */ }
    }

    const handleToggleStar = async (op: ThreadSummary) => {
        setMenuOpenId(null)
        const next = !op.is_starred
        try {
            await apiUpdateThread(op.id, { is_starred: next })
            setThreads(prev => prev.map(t => t.id === op.id ? { ...t, is_starred: next } : t))
        } catch { /* swallow */ }
    }

    const handleTogglePin = async (op: ThreadSummary) => {
        setMenuOpenId(null)
        const next = !op.is_pinned
        try {
            await apiUpdateThread(op.id, { is_pinned: next })
            setThreads(prev => prev.map(t => t.id === op.id ? { ...t, is_pinned: next } : t))
        } catch { /* swallow */ }
    }

    const handleArchive = async (op: ThreadSummary) => {
        setMenuOpenId(null)
        try {
            await apiUpdateThread(op.id, { status: 'archived' })
            setThreads(prev => prev.map(t => t.id === op.id ? { ...t, status: 'archived' } : t))
            if (selectedOpId === op.id) setSelectedOpId(null)
        } catch { /* swallow */ }
    }

    const handleUnarchive = async (op: ThreadSummary) => {
        setMenuOpenId(null)
        try {
            await apiUpdateThread(op.id, { status: 'active' })
            setThreads(prev => prev.map(t => t.id === op.id ? { ...t, status: 'active' } : t))
        } catch { /* swallow */ }
    }

    // ── Derived lists ──────────────────────────────────────────────────
    const visibleThreads = showArchived
        ? threads.filter(t => t.status === 'archived')
        : threads.filter(t => t.status !== 'archived')
    const activeCount = threads.filter(t => t.status === 'active').length
    const archivedCount = threads.filter(t => t.status === 'archived').length
    const filteredThreads = visibleThreads
        .filter(t => (t.title ?? '').toLowerCase().includes(searchQuery.toLowerCase()))
        // Sort: pinned first, then by updated_at desc
        .sort((a, b) => {
            if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        })

    return (
        <DashboardLayout>
            <PageTransition className="flex h-full w-full overflow-hidden">
                {/* Left Panel: Operation List (MomoTalk Style) */}
                <aside className={cn(
                    "w-full md:w-[320px] lg:w-[380px] flex flex-col border-r backdrop-blur-xl z-20 transition-all absolute md:relative h-full",
                    selectedOpId ? "hidden md:flex" : "flex",
                    "border-rose-900/20 bg-[#0d1117]"
                )}>
                    {/* Header */}
                    <div className={cn("p-4 border-b flex flex-col gap-4", "border-rose-900/20")}>
                        <div className="flex items-center justify-between">
                            <h1 className="text-xl font-black tracking-widest text-page-title">
                                {showArchived ? 'ARCHIVED' : 'OPERATIONS'}
                            </h1>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => { setShowArchived(v => !v); setSearchQuery('') }}
                                    title={showArchived ? 'Show active' : 'Show archived'}
                                    className={cn(
                                        "p-2 rounded-full transition-colors",
                                        showArchived
                                            ? "bg-amber-600/20 text-amber-400 hover:bg-amber-600/30"
                                            : "text-slate-400 hover:bg-rose-900/20 hover:text-rose-400"
                                    )}
                                >
                                    <Archive size={18} />
                                </button>
                                {!showArchived && (
                                    <button
                                        onClick={handleNewOperation}
                                        className={cn(
                                            "p-2 rounded-full transition-colors",
                                            "bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-900/20"
                                        )}
                                    >
                                        <Plus size={20} />
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Search Bar */}
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 text-slate-400 w-4 h-4" />
                            <input
                                placeholder="Search operations..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 rounded-xl border text-sm font-bold focus:outline-none focus:ring-2 transition-all bg-[var(--page-search-bg)] border-[var(--page-search-border)] text-[var(--page-search-text)] placeholder:text-[var(--page-search-placeholder)] focus:ring-[var(--page-search-focus-ring)]"
                            />
                        </div>
                    </div>

                    {/* Chat List */}
                    <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className={cn("h-6 w-6 animate-spin", "text-rose-500")} />
                            </div>
                        ) : filteredThreads.length === 0 ? (
                            <div className="text-center py-12 text-sm text-page-muted font-bold">
                                {filteredThreads.length === 0 && visibleThreads.length > 0
                                    ? 'No matches'
                                    : showArchived
                                        ? 'No archived operations'
                                        : 'No operations yet'
                                }
                            </div>
                        ) : (
                            filteredThreads.map((op) => (
                                <div
                                    key={op.id}
                                    onClick={() => { if (!renamingId) { setSelectedOpId(op.id); setMissionKey(k => k + 1); router.replace(`/operation/${op.id}`) } }}
                                    className={cn(
                                        "group relative p-3 rounded-xl cursor-pointer transition-all flex items-center gap-3",
                                        selectedOpId === op.id
                                            ? "bg-rose-900/10 border border-rose-900/20"
                                            : "hover:bg-rose-900/5 border border-transparent",
                                    )}
                                >
                                    {/* Avatar */}
                                    <div className="relative shrink-0">
                                        <div className={cn(
                                            "w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold text-white shadow-sm",
                                            "bg-gradient-to-br from-rose-500 to-red-700"
                                        )}>
                                            {(op.title ?? 'OP').substring(0, 2).toUpperCase()}
                                        </div>
                                        <span className={cn(
                                            "absolute bottom-0 right-0 w-3 h-3 border-2 rounded-full",
                                            "border-[#0d1117]",
                                            op.status === 'active' ? "bg-green-500" : "bg-slate-400"
                                        )} />
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-center mb-0.5">
                                            {renamingId === op.id ? (
                                                <div className="flex items-center gap-1 flex-1 min-w-0" onClick={e => e.stopPropagation()}>
                                                    <input
                                                        ref={renameInputRef}
                                                        value={renameValue}
                                                        onChange={e => setRenameValue(e.target.value)}
                                                        onKeyDown={e => handleRenameKeyDown(e, op.id)}
                                                        onBlur={() => handleRenameConfirm(op.id)}
                                                        maxLength={120}
                                                        className={cn(
                                                            "flex-1 min-w-0 text-sm font-bold rounded-lg px-2 py-0.5 outline-none ring-1",
                                                            "bg-[#010409] text-slate-200 ring-rose-500/50 focus:ring-rose-500"
                                                        )}
                                                    />
                                                    <button onClick={() => handleRenameConfirm(op.id)} className="p-0.5 rounded hover:bg-emerald-500/20 text-emerald-500">
                                                        <Check size={14} />
                                                    </button>
                                                    <button onClick={() => setRenamingId(null)} className="p-0.5 rounded hover:bg-red-500/20 text-red-400">
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                            ) : (
                                                <>
                                                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                                                        {op.is_pinned && <Pin size={12} className={cn("shrink-0", "text-rose-400")} />}
                                                        {op.is_starred && <Star size={12} className="shrink-0 text-amber-400 fill-amber-400" />}
                                                        <h3 className="font-bold text-sm truncate text-page-card-title flex-1 min-w-0">
                                                            {op.title ?? 'Untitled Operation'}
                                                        </h3>
                                                    </div>
                                                    <span className="text-[10px] font-bold text-page-muted shrink-0 ml-2">{relativeTime(op.updated_at)}</span>
                                                </>
                                            )}
                                        </div>
                                        {renamingId !== op.id && (
                                            <p className="text-xs truncate font-medium text-page-card-subtitle">
                                                {op.status === 'active' ? 'Active conversation' : 'Archived'}
                                            </p>
                                        )}
                                    </div>

                                    {/* ··· Menu trigger (visible on hover) */}
                                    {renamingId !== op.id && (
                                        <div className="relative shrink-0" onClick={e => e.stopPropagation()}>
                                            <button
                                                onClick={() => setMenuOpenId(menuOpenId === op.id ? null : op.id)}
                                                className={cn(
                                                    "p-1.5 rounded-lg transition-all",
                                                    menuOpenId === op.id
                                                        ? "bg-rose-900/20 text-rose-400"
                                                        : "opacity-0 group-hover:opacity-100",
                                                    "hover:bg-rose-900/20 text-slate-400 hover:text-rose-400"
                                                )}
                                            >
                                                <MoreHorizontal size={16} />
                                            </button>

                                            {/* Dropdown menu */}
                                            {menuOpenId === op.id && (
                                                <div
                                                    ref={menuRef}
                                                    className={cn(
                                                        "absolute right-0 top-full mt-1 z-50 w-44 rounded-xl border shadow-xl py-1 backdrop-blur-xl animate-in fade-in slide-in-from-top-1 duration-150",
                                                        "bg-[#161b22] border-rose-900/30 shadow-black/40"
                                                    )}
                                                >
                                                    <MenuBtn icon={<Pencil size={14} />} label="Rename" onClick={() => handleRenameStart(op)} />
                                                    <MenuBtn icon={<Star size={14} className={op.is_starred ? "fill-amber-400 text-amber-400" : ""} />} label={op.is_starred ? "Unstar" : "Star"} onClick={() => handleToggleStar(op)} />
                                                    <MenuBtn icon={<Pin size={14} className={op.is_pinned ? "text-rose-400" : ""} />} label={op.is_pinned ? "Unpin" : "Pin to top"} onClick={() => handleTogglePin(op)} />
                                                    {op.status === 'archived'
                                                        ? <MenuBtn icon={<ArchiveRestore size={14} />} label="Unarchive" onClick={() => handleUnarchive(op)} />
                                                        : <MenuBtn icon={<Archive size={14} />} label="Archive" onClick={() => handleArchive(op)} />
                                                    }
                                                    <div className={cn("my-1 h-px", "bg-rose-900/20")} />
                                                    <MenuBtn icon={<Trash2 size={14} />} label="Delete" danger onClick={() => handleDelete(op.id)} />
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    {/* Footer Stats similar to MomoTalk */}
                    <div className={cn(
                        "p-3 border-t flex justify-between items-center text-[10px] font-bold uppercase tracking-wider",
                        "bg-[#010409] border-rose-900/20 text-slate-600"
                    )}>
                        <span>
                            {showArchived
                                ? `${archivedCount} Archived`
                                : `${activeCount} Active`
                            }
                        </span>
                        <span>Ver 2.0</span>
                    </div>
                </aside>

                {/* Right Panel: Active Chat Area */}
                <main className={cn(
                    "flex-1 min-w-0 relative flex flex-col transition-colors overflow-hidden",
                    !selectedOpId ? "hidden md:flex" : "flex",
                    "bg-[#0d1117]/50"
                )}>
                    {selectedOpId ? (
                        <MissionControl
                            key={missionKey}
                            threadId={selectedOpId}
                            onBack={handleBackToList}
                            onThreadCreated={handleThreadCreated}
                            onMessageComplete={handleMessageComplete}
                        />
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                            <div className={cn("w-32 h-32 rounded-full flex items-center justify-center mb-6", "bg-white/5")}>
                                <MessageSquare size={48} className="opacity-20" />
                            </div>
                            <p className="font-bold tracking-widest text-sm text-page-muted">SELECT AN OPERATION</p>
                        </div>
                    )}
                </main>
            </PageTransition>
        </DashboardLayout>
    )
}

/* ═══════════════════════════════════════════════════════════════════
 * MenuBtn — Reusable context-menu row
 * ═══════════════════════════════════════════════════════════════════ */

function MenuBtn({ icon, label, danger, onClick }: {
    icon: React.ReactNode; label: string; danger?: boolean; onClick: () => void
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold transition-colors text-left",
                danger
                    ? "text-red-400 hover:bg-red-500/10"
                    : "text-slate-300 hover:bg-rose-900/15 hover:text-slate-100"
            )}
        >
            {icon}
            {label}
        </button>
    )
}
