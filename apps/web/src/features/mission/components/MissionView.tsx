"use client"

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { motion, AnimatePresence } from 'framer-motion'
import {
    AlertTriangle,
    Bot,
    Calendar as CalendarIcon,
    CheckCircle2,
    ChevronLeft,
    ChevronRight,
    Clock,
    Filter,
    Kanban,
    Loader2,
    Plus,
    Table2,
    Target,
    Trash2,
    Trophy,
    X,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMissionStore, type Mission, type MissionStatus, type MissionPriority } from '@/features/mission/store'
import {
    PRIORITY_CONFIG,
    STATUS_CONFIG,
    isOverdue,
    formatDuration,
    formatDeadline,
    getCategoryColor,
} from '@/types/mission'
import { toast } from '@/shared/hooks/use-toast'
import { useAffinityTracker } from '@/features/emotional/hooks/use-affinity-tracker'

/* ═══════════════════════════════════════════════════════════════════
 * Main Page
 * ═══════════════════════════════════════════════════════════════════ */
type TabFilter = 'active' | 'completed' | 'all'

export function MissionView() {
    const {
        missions, stats, loading,
        fetchMissions, fetchStats, createMission, updateMission, deleteMission, toggleStep, reorderMissions,
        viewMode, setViewMode,
        filterCategory, setFilterCategory,
        filterPriority, setFilterPriority,
    } = useMissionStore()

    const { recordMissionStep } = useAffinityTracker()

    const [activeTab, setActiveTab] = useState<TabFilter>('active')
    const [showCreateForm, setShowCreateForm] = useState(false)
    const [expandedMission, setExpandedMission] = useState<string | null>(null)
    const [showFilters, setShowFilters] = useState(false)
    const [calendarDate, setCalendarDate] = useState(new Date())

    useEffect(() => {
        fetchMissions()
        fetchStats()
    }, [fetchMissions, fetchStats])

    // Filter missions by tab + filters
    const filteredMissions = useMemo(() => {
        let list = missions
        if (activeTab === 'active') list = list.filter((m) => m.status === 'active' || m.status === 'draft')
        else if (activeTab === 'completed') list = list.filter((m) => m.status === 'completed' || m.status === 'archived')
        if (filterCategory) list = list.filter((m) => m.category === filterCategory)
        if (filterPriority) list = list.filter((m) => m.priority === filterPriority)
        return list
    }, [missions, activeTab, filterCategory, filterPriority])

    // Stats
    const totalActive = stats?.active ?? missions.filter((m) => m.status === 'active').length
    const totalCompleted = stats?.completed ?? missions.filter((m) => m.status === 'completed').length
    const totalOverdue = stats?.overdue ?? missions.filter(isOverdue).length
    const categories = stats?.categories ?? []
    const overallProgress = missions.length > 0
        ? Math.round(missions.reduce((sum, m) => sum + m.progress, 0) / missions.length)
        : 0

    const handleStatusCycle = useCallback(async (mission: Mission) => {
        const nextStatus: Record<MissionStatus, MissionStatus> = {
            draft: 'active', active: 'completed', completed: 'archived', archived: 'active',
        }
        await updateMission(mission.id, { status: nextStatus[mission.status] })
        toast({ title: `Mission → ${nextStatus[mission.status].toUpperCase()}` })
    }, [updateMission])

    const handleDelete = useCallback(async (id: string) => {
        const ok = await deleteMission(id)
        if (ok) toast({ title: 'Mission deleted' })
    }, [deleteMission])

    const handleToggleStep = useCallback(async (missionId: string, stepIdx: number) => {
        const result = await toggleStep(missionId, stepIdx)
        // Award affinity if step was completed (not uncompleted)
        if (result && result.steps[stepIdx]?.done) {
            recordMissionStep()
        }
    }, [toggleStep, recordMissionStep])

    const handleInlineUpdate = useCallback(async (id: string, data: Partial<Mission>) => {
        await updateMission(id, data)
    }, [updateMission])

    return (
        <DashboardLayout>
            <PageTransition className="flex-1 overflow-y-auto p-4 md:p-8">
                {/* Header */}
                <header className="mb-6 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                    <div>
                        <h1 className="text-lg font-black tracking-widest mb-1 text-page-title">
                            MISSION CONTROL
                        </h1>
                        <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">
                            Plan, schedule, and track your goals — Notion-style.
                        </p>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                        {/* View Switcher */}
                        <ViewSwitcher viewMode={viewMode} setViewMode={setViewMode} />

                        {/* Tab Switcher */}
                        <div className={cn("p-1 rounded-xl flex", "bg-[#0d1117] border border-rose-900/40")}>
                            <TabButton active={activeTab === 'active'} onClick={() => setActiveTab('active')} label="Active" count={totalActive} />
                            <TabButton active={activeTab === 'completed'} onClick={() => setActiveTab('completed')} label="Done" count={totalCompleted} />
                            <TabButton active={activeTab === 'all'} onClick={() => setActiveTab('all')} label="All" count={missions.length} />
                        </div>
                    </div>
                </header>

                {/* Stats Bar */}
                <div className={cn(
                    "mb-6 p-5 rounded-2xl relative overflow-hidden transition-all",
                    "bg-gradient-to-r from-rose-600/90 to-red-800/90 shadow-lg shadow-rose-900/20 text-white"
                )}>
                    <div className="relative z-10 flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-8">
                            <div>
                                <div className="text-[10px] font-bold opacity-60 uppercase tracking-wider">Progress</div>
                                <div className="text-3xl font-black tracking-tighter">{overallProgress}%</div>
                            </div>
                            <div className="flex gap-6 text-sm">
                                <StatPill label="Active" value={totalActive} />
                                <StatPill label="Done" value={totalCompleted} />
                                {totalOverdue > 0 && (
                                    <StatPill label="Overdue" value={totalOverdue} alert />
                                )}
                            </div>
                        </div>
                        <button
                            onClick={() => setShowCreateForm(true)}
                            className="px-5 py-2.5 bg-white/20 hover:bg-white/30 rounded-xl font-bold text-sm flex items-center gap-2 transition-colors backdrop-blur-sm"
                        >
                            <Plus size={16} /> New Mission
                        </button>
                    </div>
                    <Trophy className="absolute -bottom-8 -right-8 w-36 h-36 opacity-[0.08] rotate-12" />
                </div>

                {/* Filter Bar */}
                <div className="mb-5 flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors",
                            showFilters
                                ? "bg-rose-600 text-white"
                                : "bg-slate-800 text-slate-400 hover:text-rose-400"
                        )}
                    >
                        <Filter size={13} /> Filters
                        {(filterCategory || filterPriority) && (
                            <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        )}
                    </button>

                    <AnimatePresence>
                        {showFilters && (
                            <motion.div
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                className="flex items-center gap-2 overflow-hidden"
                            >
                                {/* Category filter */}
                                {categories.length > 0 && (
                                    <select
                                        value={filterCategory ?? ''}
                                        onChange={(e) => setFilterCategory(e.target.value || null)}
                                        className={cn(
                                            "text-xs font-bold px-3 py-1.5 rounded-lg outline-none appearance-none cursor-pointer",
                                            "bg-slate-800 text-slate-300 border border-slate-700"
                                        )}
                                    >
                                        <option value="">All Categories</option>
                                        {categories.map((c) => (
                                            <option key={c} value={c}>{c}</option>
                                        ))}
                                    </select>
                                )}

                                {/* Priority filter */}
                                <select
                                    value={filterPriority ?? ''}
                                    onChange={(e) => setFilterPriority((e.target.value || null) as MissionPriority | null)}
                                    className={cn(
                                        "text-xs font-bold px-3 py-1.5 rounded-lg outline-none appearance-none cursor-pointer",
                                        "bg-slate-800 text-slate-300 border border-slate-700"
                                    )}
                                >
                                    <option value="">All Priorities</option>
                                    <option value="critical">🔴 Critical</option>
                                    <option value="normal">🔵 Normal</option>
                                    <option value="low">⚪ Low</option>
                                </select>

                                {/* Clear */}
                                {(filterCategory || filterPriority) && (
                                    <button
                                        onClick={() => { setFilterCategory(null); setFilterPriority(null) }}
                                        className={cn("text-xs px-2 py-1 rounded-lg", "text-rose-400 hover:bg-rose-900/20")}
                                    >
                                        Clear
                                    </button>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Loading state */}
                {loading && missions.length === 0 && (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className={cn("w-8 h-8 animate-spin", "text-rose-500")} />
                    </div>
                )}

                {/* Empty state */}
                {!loading && filteredMissions.length === 0 && (
                    <div className={cn("text-center py-16", "text-slate-500")}>
                        <Target className="w-16 h-16 mx-auto mb-4 opacity-30" />
                        <p className="text-lg font-bold mb-1">No missions yet</p>
                        <p className="text-sm mb-4">Create one or let the agent generate missions from your conversations.</p>
                        <button
                            onClick={() => setShowCreateForm(true)}
                            className={cn(
                                "px-6 py-2.5 rounded-xl font-bold text-sm inline-flex items-center gap-2",
                                "bg-rose-600 text-white hover:bg-rose-700"
                            )}
                        >
                            <Plus size={16} /> Create First Mission
                        </button>
                    </div>
                )}

                {/* ── VIEW RENDERER ── */}
                {filteredMissions.length > 0 && (
                    <>
                        {viewMode === 'board' && (
                            <BoardView
                                missions={filteredMissions}
                                expandedMission={expandedMission}
                                setExpandedMission={setExpandedMission}
                                onStatusCycle={handleStatusCycle}
                                onDelete={handleDelete}
                                onToggleStep={handleToggleStep}
                                onUpdate={handleInlineUpdate}
                            />
                        )}
                        {viewMode === 'table' && (
                            <TableView
                                missions={filteredMissions}
                                onStatusCycle={handleStatusCycle}
                                onDelete={handleDelete}
                                onUpdate={handleInlineUpdate}
                            />
                        )}
                        {viewMode === 'calendar' && (
                            <CalendarView
                                missions={filteredMissions}
                                calendarDate={calendarDate}
                                setCalendarDate={setCalendarDate}
                                onStatusCycle={handleStatusCycle}
                            />
                        )}
                    </>
                )}

                {/* Create Mission Modal */}
                <AnimatePresence>
                    {showCreateForm && (
                        <CreateMissionModal
                            categories={categories}
                            onClose={() => setShowCreateForm(false)}
                            onCreate={async (data) => {
                                await createMission(data)
                                setShowCreateForm(false)
                                toast({ title: 'Mission created!' })
                            }}
                        />
                    )}
                </AnimatePresence>
            </PageTransition>
        </DashboardLayout>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * Shared Sub-components
 * ═══════════════════════════════════════════════════════════════════ */

function StatPill({ label, value, alert }: { label: string; value: number; alert?: boolean }) {
    return (
        <div className={cn("flex flex-col items-center", alert && "text-yellow-200")}>
            <span className={cn("text-xl font-black", alert && "text-yellow-200")}>{value}</span>
            <span className="text-[10px] font-bold opacity-60 uppercase">{label}</span>
        </div>
    )
}

function ViewSwitcher({ viewMode, setViewMode }: {
    viewMode: string; setViewMode: (m: 'board' | 'table' | 'calendar') => void
}) {
    const views = [
        { key: 'board' as const, icon: Kanban, label: 'Board' },
        { key: 'table' as const, icon: Table2, label: 'Table' },
        { key: 'calendar' as const, icon: CalendarIcon, label: 'Calendar' },
    ]
    return (
        <div className={cn("p-1 rounded-xl flex gap-0.5", "bg-[#0d1117] border border-rose-900/40")}>
            {views.map(({ key, icon: Icon, label }) => (
                <button
                    key={key}
                    onClick={() => setViewMode(key)}
                    title={label}
                    className={cn(
                        "p-2 rounded-lg transition-all",
                        viewMode === key
                            ? "bg-rose-600 text-white shadow-sm"
                            : "text-slate-500 hover:text-rose-400"
                    )}
                >
                    <Icon size={16} />
                </button>
            ))}
        </div>
    )
}

function TabButton({ active, onClick, label, count }: {
    active: boolean; onClick: () => void; label: string; count: number
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2",
                active
                    ? "bg-rose-600 text-white shadow-sm"
                    : "text-slate-500 hover:text-rose-400"
            )}
        >
            {label}
            <span className={cn(
                "text-[10px] px-1.5 py-0.5 rounded-full font-bold",
                active
                    ? "bg-white/20"
                    : "bg-slate-800"
            )}>
                {count}
            </span>
        </button>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * BOARD VIEW — Kanban columns by status
 * ═══════════════════════════════════════════════════════════════════ */

function BoardView({ missions, expandedMission, setExpandedMission, onStatusCycle, onDelete, onToggleStep, onUpdate }: {
    missions: Mission[]
    expandedMission: string | null
    setExpandedMission: (id: string | null) => void
    onStatusCycle: (m: Mission) => void
    onDelete: (id: string) => void
    onToggleStep: (missionId: string, idx: number) => void
    onUpdate: (id: string, data: Partial<Mission>) => void
}) {
    const columns: { status: MissionStatus; label: string }[] = [
        { status: 'draft', label: 'Backlog' },
        { status: 'active', label: 'In Progress' },
        { status: 'completed', label: 'Done' },
    ]

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {columns.map(({ status, label }) => {
                const colMissions = missions.filter((m) => m.status === status)
                const colConfig = STATUS_CONFIG[status]
                return (
                    <div key={status} className={cn(
                        "rounded-2xl p-3 min-h-[200px]",
                        "bg-[#0d1117]/40"
                    )}>
                        <div className="flex items-center gap-2 mb-3 px-1">
                            <div className="w-2.5 h-2.5 rounded-full" style={{ background: colConfig.accent }} />
                            <h3 className={cn("text-xs font-black uppercase tracking-wider", "text-slate-400")}>
                                {label}
                            </h3>
                            <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-auto", "bg-slate-800 text-slate-500")}>
                                {colMissions.length}
                            </span>
                        </div>

                        <div className="space-y-2">
                            <AnimatePresence mode="popLayout">
                                {colMissions.map((mission) => (
                                    <MissionCard
                                        key={mission.id}
                                        mission={mission}
                                        expanded={expandedMission === mission.id}
                                        onToggleExpand={() => setExpandedMission(expandedMission === mission.id ? null : mission.id)}
                                        onStatusCycle={() => onStatusCycle(mission)}
                                        onDelete={() => onDelete(mission.id)}
                                        onToggleStep={(idx) => onToggleStep(mission.id, idx)}
                                        onUpdate={(data) => onUpdate(mission.id, data)}
                                    />
                                ))}
                            </AnimatePresence>
                            {colMissions.length === 0 && (
                                <p className={cn("text-center text-xs py-8 opacity-40", "text-slate-600")}>
                                    No missions
                                </p>
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * TABLE VIEW — Notion-style spreadsheet
 * ═══════════════════════════════════════════════════════════════════ */

function TableView({ missions, onStatusCycle, onDelete, onUpdate }: {
    missions: Mission[]
    onStatusCycle: (m: Mission) => void
    onDelete: (id: string) => void
    onUpdate: (id: string, data: Partial<Mission>) => void
}) {
    return (
        <div className={cn("rounded-2xl overflow-hidden border mb-6", "border-rose-900/20 bg-[#0d1117]/60")}>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className={cn("text-[10px] font-black uppercase tracking-wider", "bg-slate-900 text-slate-500")}>
                            <th className="text-left px-4 py-3 w-8"></th>
                            <th className="text-left px-4 py-3">Title</th>
                            <th className="text-left px-3 py-3 w-24">Status</th>
                            <th className="text-left px-3 py-3 w-24">Priority</th>
                            <th className="text-left px-3 py-3 w-28">Category</th>
                            <th className="text-left px-3 py-3 w-16">Meet</th>
                            <th className="text-left px-3 py-3 w-28">Deadline</th>
                            <th className="text-left px-3 py-3 w-20">Time Est.</th>
                            <th className="text-left px-3 py-3 w-20">Progress</th>
                            <th className="text-left px-3 py-3 w-10"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {missions.map((m) => {
                            const prio = PRIORITY_CONFIG[m.priority]
                            const stat = STATUS_CONFIG[m.status]
                            const overdue = isOverdue(m)
                            return (
                                <tr
                                    key={m.id}
                                    className={cn(
                                        "border-t transition-colors group",
                                        overdue && "bg-red-900/10",
                                        "border-slate-800 hover:bg-slate-800/50"
                                    )}
                                >
                                    {/* Status circle */}
                                    <td className="px-4 py-3">
                                        <button
                                            onClick={() => onStatusCycle(m)}
                                            className={cn(
                                                "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors",
                                                m.status === 'completed'
                                                    ? "bg-rose-600 border-rose-600 text-white"
                                                    : "border-slate-600 hover:border-rose-500"
                                            )}
                                        >
                                            {m.status === 'completed' && <CheckCircle2 size={12} />}
                                        </button>
                                    </td>
                                    {/* Title */}
                                    <td className="px-4 py-3">
                                        <div className="flex items-center gap-2">
                                            <span className={cn(
                                                "font-semibold truncate max-w-[300px]",
                                                m.status === 'completed' && "line-through opacity-50",
                                                "text-slate-200"
                                            )}>
                                                {m.title}
                                            </span>
                                            {m.source === 'agent' && <Bot size={12} className="text-rose-400" />}
                                            {overdue && <AlertTriangle size={12} className="text-red-500" />}
                                        </div>
                                        {m.tags.length > 0 && (
                                            <div className="flex gap-1 mt-0.5">
                                                {m.tags.slice(0, 3).map((t) => (
                                                    <span key={t} className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium", "bg-slate-800 text-slate-500")}>{t}</span>
                                                ))}
                                            </div>
                                        )}
                                    </td>
                                    {/* Status */}
                                    <td className="px-3 py-3">
                                        <span className={cn("text-[10px] uppercase font-bold px-2 py-1 rounded", stat.darkColor)}>
                                            {stat.label}
                                        </span>
                                    </td>
                                    {/* Priority */}
                                    <td className="px-3 py-3">
                                        <span className={cn("text-[10px] uppercase font-bold px-2 py-1 rounded", prio.darkColor)}>
                                            {prio.label}
                                        </span>
                                    </td>
                                    {/* Category */}
                                    <td className="px-3 py-3">
                                        {m.category ? (
                                            <span className={cn("text-[10px] font-bold px-2 py-1 rounded", getCategoryColor(m.category).bg, getCategoryColor(m.category).text)}>
                                                {m.category}
                                            </span>
                                        ) : (
                                            <span className={cn("text-[10px] opacity-30", "text-slate-600")}>—</span>
                                        )}
                                    </td>
                                    {/* Meet URL */}
                                    <td className="px-3 py-3">
                                        {m.meet_url ? (
                                            <a
                                                href={m.meet_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className={cn(
                                                    "inline-flex items-center justify-center w-6 h-6 rounded-md transition-colors",
                                                    "bg-rose-900/30 text-rose-400 hover:bg-rose-600 hover:text-white"
                                                )}
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <CalendarIcon size={12} />
                                            </a>
                                        ) : (
                                            <span className={cn("text-[10px] opacity-30", "text-slate-600")}>—</span>
                                        )}
                                    </td>
                                    {/* Deadline */}
                                    <td className="px-3 py-3">
                                        {m.deadline ? (
                                            <span className={cn(
                                                "text-xs font-semibold",
                                                overdue ? "text-red-500" : "text-slate-400"
                                            )}>
                                                {formatDeadline(m.deadline)}
                                            </span>
                                        ) : (
                                            <span className={cn("text-[10px] opacity-30", "text-slate-600")}>—</span>
                                        )}
                                    </td>
                                    {/* Time estimate */}
                                    <td className="px-3 py-3">
                                        <span className={cn("text-xs", "text-slate-500")}>
                                            {formatDuration(m.estimated_minutes) || '—'}
                                        </span>
                                    </td>
                                    {/* Progress */}
                                    <td className="px-3 py-3">
                                        <div className="flex items-center gap-2">
                                            <div className={cn("w-16 h-1.5 rounded-full overflow-hidden", "bg-slate-800")}>
                                                <div
                                                    className={cn("h-full rounded-full transition-all", "bg-rose-500")}
                                                    style={{ width: `${m.progress}%` }}
                                                />
                                            </div>
                                            <span className={cn("text-[10px] font-bold", "text-slate-500")}>{m.progress}%</span>
                                        </div>
                                    </td>
                                    {/* Delete */}
                                    <td className="px-3 py-3">
                                        <button
                                            onClick={() => onDelete(m.id)}
                                            className={cn("opacity-0 group-hover:opacity-100 p-1 rounded transition-all", "text-red-400 hover:bg-red-900/20")}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * CALENDAR VIEW — Month grid showing missions by deadline
 * ═══════════════════════════════════════════════════════════════════ */

function CalendarView({ missions, calendarDate, setCalendarDate, onStatusCycle }: {
    missions: Mission[]
    calendarDate: Date
    setCalendarDate: (d: Date) => void
    onStatusCycle: (m: Mission) => void
}) {
    const year = calendarDate.getFullYear()
    const month = calendarDate.getMonth()
    const firstDay = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    const monthName = calendarDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })

    // Group missions by deadline day
    const missionsByDay = useMemo(() => {
        const map: Record<string, Mission[]> = {}
        for (const m of missions) {
            if (!m.deadline) continue
            const d = new Date(m.deadline)
            if (d.getFullYear() === year && d.getMonth() === month) {
                const key = String(d.getDate())
                if (!map[key]) map[key] = []
                map[key].push(m)
            }
        }
        return map
    }, [missions, year, month])

    const prevMonth = () => setCalendarDate(new Date(year, month - 1, 1))
    const nextMonth = () => setCalendarDate(new Date(year, month + 1, 1))

    const days: (number | null)[] = []
    for (let i = 0; i < firstDay; i++) days.push(null)
    for (let d = 1; d <= daysInMonth; d++) days.push(d)

    return (
        <div className={cn("rounded-2xl border overflow-hidden mb-6", "border-rose-900/20 bg-[#0d1117]/60")}>
            {/* Month nav */}
            <div className={cn("flex items-center justify-between px-5 py-3", "bg-slate-900")}>
                <button onClick={prevMonth} className={cn("p-1.5 rounded-lg transition-colors", "text-slate-400 hover:bg-slate-800")}>
                    <ChevronLeft size={18} />
                </button>
                <h3 className={cn("text-sm font-black uppercase tracking-wider", "text-slate-300")}>
                    {monthName}
                </h3>
                <button onClick={nextMonth} className={cn("p-1.5 rounded-lg transition-colors", "text-slate-400 hover:bg-slate-800")}>
                    <ChevronRight size={18} />
                </button>
            </div>

            {/* Weekday headers */}
            <div className="grid grid-cols-7 text-center">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                    <div key={d} className={cn("text-[10px] font-bold uppercase py-2", "text-slate-600")}>
                        {d}
                    </div>
                ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7">
                {days.map((day, i) => {
                    if (day === null) return <div key={`empty-${i}`} className={cn("min-h-[90px] border-t", "border-slate-800")} />
                    const dayStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                    const isToday = dayStr === todayStr
                    const dayMissions = missionsByDay[String(day)] || []
                    return (
                        <div
                            key={day}
                            className={cn(
                                "min-h-[90px] border-t p-1.5 transition-colors",
                                "border-slate-800",
                                isToday && "bg-rose-900/10"
                            )}
                        >
                            <span className={cn(
                                "text-xs font-bold block mb-1",
                                isToday
                                    ? "text-rose-400"
                                    : "text-slate-500"
                            )}>
                                {day}
                            </span>
                            {dayMissions.slice(0, 3).map((m) => {
                                const overdue = isOverdue(m)
                                return (
                                    <button
                                        key={m.id}
                                        onClick={() => onStatusCycle(m)}
                                        className={cn(
                                            "block w-full text-left text-[10px] font-semibold px-1.5 py-0.5 rounded mb-0.5 truncate transition-colors",
                                            overdue
                                                ? "bg-red-900/30 text-red-400"
                                                : m.status === 'completed'
                                                    ? "bg-emerald-900/30 text-emerald-400 line-through opacity-60"
                                                    : "bg-rose-900/20 text-rose-400 hover:bg-rose-900/30"
                                        )}
                                    >
                                        {m.title}
                                    </button>
                                )
                            })}
                            {dayMissions.length > 3 && (
                                <span className={cn("text-[9px] font-bold", "text-slate-600")}>
                                    +{dayMissions.length - 3} more
                                </span>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Missions without deadlines note */}
            {missions.some((m) => !m.deadline) && (
                <div className={cn("px-5 py-3 text-xs border-t", "border-slate-800 text-slate-600")}>
                    {missions.filter((m) => !m.deadline).length} mission(s) without deadlines — assign dates to see them on the calendar.
                </div>
            )}
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * MISSION CARD — Used in Board view
 * ═══════════════════════════════════════════════════════════════════ */

function MissionCard({ mission, expanded, onToggleExpand, onStatusCycle, onDelete, onToggleStep, onUpdate }: {
    mission: Mission
    expanded: boolean
    onToggleExpand: () => void
    onStatusCycle: () => void
    onDelete: () => void
    onToggleStep: (idx: number) => void
    onUpdate: (data: Partial<Mission>) => void
}) {
    const prio = PRIORITY_CONFIG[mission.priority]
    const isComplete = mission.status === 'completed' || mission.status === 'archived'
    const hasSteps = mission.steps.length > 0
    const doneSteps = mission.steps.filter((s) => s.done).length
    const overdue = isOverdue(mission)

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={cn(
                "group rounded-xl transition-all overflow-hidden",
                overdue && !isComplete && "ring-1 ring-red-500/40",
                "bg-[#0d1117]/80 border border-rose-900/15 hover:border-rose-900/40"
            )}
        >
            {/* Main row */}
            <div className="p-3 cursor-pointer" onClick={onToggleExpand} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onToggleExpand()}>
                <div className="flex items-start gap-2 mb-2">
                    {/* Status button */}
                    <button
                        onClick={(e) => { e.stopPropagation(); onStatusCycle() }}
                        className={cn(
                            "mt-0.5 w-5 h-5 rounded-full flex items-center justify-center shrink-0 border-2 transition-colors",
                            isComplete
                                ? "bg-rose-600 border-rose-600 text-white"
                                : "border-slate-700 hover:border-rose-500"
                        )}
                    >
                        {isComplete && <CheckCircle2 size={12} />}
                    </button>

                    <div className="flex-1 min-w-0">
                        <h4 className={cn(
                            "font-bold text-sm leading-tight",
                            isComplete && "line-through opacity-50",
                            "text-slate-200"
                        )}>
                            {mission.title}
                        </h4>
                    </div>

                    {mission.source === 'agent' && (
                        <Bot size={12} className={cn("shrink-0 mt-0.5", "text-rose-400")} />
                    )}
                </div>

                {/* Metadata row */}
                <div className="flex items-center gap-1.5 flex-wrap">
                    <span className={cn("text-[9px] uppercase font-bold px-1.5 py-0.5 rounded", prio.darkColor)}>
                        {prio.label}
                    </span>
                    {mission.category && (
                        <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", getCategoryColor(mission.category).bg, getCategoryColor(mission.category).text)}>
                            {mission.category}
                        </span>
                    )}
                    {mission.meet_url && (
                        <a
                            href={mission.meet_url}
                            target="_blank"
                            rel="noreferrer"
                            className={cn(
                                "flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded transition-colors",
                                "bg-rose-900/30 text-rose-400 hover:bg-rose-600 hover:text-white"
                            )}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <CalendarIcon size={10} /> Link
                        </a>
                    )}
                    {mission.tags.slice(0, 2).map((tag) => (
                        <span key={tag} className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium", "bg-slate-800 text-slate-500")}>
                            {tag}
                        </span>
                    ))}
                </div>

                {/* Deadline + time row */}
                {(mission.deadline || mission.estimated_minutes) && (
                    <div className="flex items-center gap-3 mt-2">
                        {mission.deadline && (
                            <span className={cn(
                                "flex items-center gap-1 text-[10px] font-semibold",
                                overdue ? "text-red-500" : "text-slate-500"
                            )}>
                                <CalendarIcon size={10} />
                                {formatDeadline(mission.deadline)}
                            </span>
                        )}
                        {mission.estimated_minutes && (
                            <span className={cn("flex items-center gap-1 text-[10px]", "text-slate-600")}>
                                <Clock size={10} />
                                {formatDuration(mission.estimated_minutes)}
                            </span>
                        )}
                    </div>
                )}

                {/* Progress bar */}
                {hasSteps && (
                    <div className="mt-2 flex items-center gap-2">
                        <div className={cn("flex-1 h-1 rounded-full overflow-hidden", "bg-slate-800")}>
                            <div
                                className={cn("h-full rounded-full transition-all", "bg-rose-500")}
                                style={{ width: `${mission.progress}%` }}
                            />
                        </div>
                        <span className={cn("text-[9px] font-bold", "text-slate-600")}>
                            {doneSteps}/{mission.steps.length}
                        </span>
                    </div>
                )}
            </div>

            {/* Expanded area */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className={cn("px-3 pb-3 pt-1 border-t", "border-rose-900/10")}>
                            {mission.description && (
                                <p className={cn("text-xs mb-2", "text-slate-400")}>{mission.description}</p>
                            )}

                            {/* Notes */}
                            {mission.notes && (
                                <div className={cn("text-xs mb-2 p-2 rounded-lg whitespace-pre-wrap", "bg-slate-900 text-slate-400")}>
                                    {mission.notes}
                                </div>
                            )}

                            {/* Inline deadline editor */}
                            <div className="flex items-center gap-3 mb-2 flex-wrap">
                                <label className={cn("text-[10px] font-bold uppercase", "text-slate-600")}>Deadline:</label>
                                <input
                                    type="datetime-local"
                                    value={mission.deadline ? new Date(mission.deadline).toISOString().slice(0, 16) : ''}
                                    onChange={(e) => onUpdate({ deadline: e.target.value ? new Date(e.target.value).toISOString() : null } as Partial<Mission>)}
                                    className={cn(
                                        "text-xs px-2 py-1 rounded-lg outline-none border",
                                        "bg-slate-900 border-slate-700 text-slate-300"
                                    )}
                                    onClick={(e) => e.stopPropagation()}
                                />
                                <label className={cn("text-[10px] font-bold uppercase", "text-slate-600")}>Estimate:</label>
                                <input
                                    type="number"
                                    min={1}
                                    max={14400}
                                    placeholder="min"
                                    value={mission.estimated_minutes ?? ''}
                                    onChange={(e) => onUpdate({ estimated_minutes: e.target.value ? Number(e.target.value) : null } as Partial<Mission>)}
                                    className={cn(
                                        "text-xs px-2 py-1 rounded-lg outline-none border w-20",
                                        "bg-slate-900 border-slate-700 text-slate-300"
                                    )}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            </div>

                            {/* Steps checklist */}
                            {hasSteps && (
                                <ul className="space-y-1 mb-2">
                                    {mission.steps.map((step, idx) => (
                                        <li key={idx} className="flex items-start gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onToggleStep(idx) }}
                                                className={cn(
                                                    "mt-0.5 w-4 h-4 rounded flex items-center justify-center shrink-0 border-2 transition-colors",
                                                    step.done
                                                        ? "bg-rose-600 border-rose-600 text-white"
                                                        : "border-slate-700 hover:border-rose-500"
                                                )}
                                            >
                                                {step.done && <CheckCircle2 size={10} />}
                                            </button>
                                            <span className={cn(
                                                "text-xs",
                                                step.done && "line-through opacity-50",
                                                "text-slate-300"
                                            )}>
                                                {step.text}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            )}

                            {/* Actions */}
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={(e) => { e.stopPropagation(); onDelete() }}
                                    className={cn(
                                        "text-[10px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors",
                                        "text-red-400 hover:bg-red-900/20"
                                    )}
                                >
                                    <Trash2 size={11} /> Delete
                                </button>
                                <span className={cn("text-[9px] ml-auto", "text-slate-700")}>
                                    Created {new Date(mission.created_at).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}


/* ═══════════════════════════════════════════════════════════════════
 * CREATE MISSION MODAL — Notion-style rich creation form
 * ═══════════════════════════════════════════════════════════════════ */

function CreateMissionModal({ categories, onClose, onCreate }: {
    categories: string[]
    onClose: () => void
    onCreate: (data: Record<string, unknown>) => Promise<void>
}) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [priority, setPriority] = useState<MissionPriority>('normal')
    const [stepsText, setStepsText] = useState('')
    const [deadline, setDeadline] = useState('')
    const [scheduledStart, setScheduledStart] = useState('')
    const [estimatedMinutes, setEstimatedMinutes] = useState('')
    const [category, setCategory] = useState('')
    const [newCategory, setNewCategory] = useState('')
    const [notes, setNotes] = useState('')
    const [meetUrl, setMeetUrl] = useState('')
    const [tagsText, setTagsText] = useState('')
    const [submitting, setSubmitting] = useState(false)

    const effectiveCategory = category === '__new__' ? newCategory.trim() : (category || null)

    const handleSubmit = async () => {
        if (!title.trim()) return
        setSubmitting(true)
        const steps = stepsText
            .split('\n')
            .map((l) => l.trim())
            .filter(Boolean)
            .map((text) => ({ text, done: false }))
        const tags = tagsText
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
        await onCreate({
            title: title.trim(),
            description: description.trim() || null,
            priority,
            steps,
            tags,
            source: 'user',
            status: 'active',
            deadline: deadline ? new Date(deadline).toISOString() : null,
            scheduled_start: scheduledStart ? new Date(scheduledStart).toISOString() : null,
            estimated_minutes: estimatedMinutes ? Number(estimatedMinutes) : null,
            category: effectiveCategory || null,
            notes: notes.trim() || null,
            meet_url: meetUrl.trim() || null,
        })
        setSubmitting(false)
    }

    const inputCn = cn(
        "w-full px-3 py-2 rounded-lg text-sm outline-none border transition-colors",
        "bg-slate-900 border-slate-800 text-slate-200 placeholder:text-slate-600 focus:border-rose-600"
    )

    const labelCn = cn("text-[10px] font-bold uppercase tracking-wider mb-1 block", "text-slate-500")

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.95, y: 20 }}
                className={cn(
                    "w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border-2 shadow-2xl",
                    "bg-[#0a0e14] border-rose-900/30"
                )}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className={cn("flex items-center justify-between px-6 py-4 border-b", "border-slate-800")}>
                    <h2 className="text-lg font-black text-page-title">New Mission</h2>
                    <button onClick={onClose} className={cn("p-1.5 rounded-lg", "text-slate-500 hover:text-rose-400 hover:bg-rose-900/20")}>
                        <X size={18} />
                    </button>
                </div>

                <div className="px-6 py-5 space-y-4">
                    {/* Title */}
                    <div>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Mission title…"
                            maxLength={200}
                            className={cn(inputCn, "text-lg font-bold")}
                            autoFocus
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className={labelCn}>Description</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="What is this mission about?"
                            rows={2}
                            maxLength={2000}
                            className={cn(inputCn, "resize-none")}
                        />
                    </div>

                    {/* Row: Priority + Category */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className={labelCn}>Priority</label>
                            <div className="flex gap-1.5">
                                {(['low', 'normal', 'critical'] as MissionPriority[]).map((p) => (
                                    <button
                                        key={p}
                                        onClick={() => setPriority(p)}
                                        className={cn(
                                            "flex-1 text-[10px] uppercase font-bold py-2 rounded-lg transition-all",
                                            priority === p
                                                ? "bg-rose-600 text-white"
                                                : "bg-slate-800 text-slate-500 hover:text-rose-400"
                                        )}
                                    >
                                        {p}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div>
                            <label className={labelCn}>Category</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className={cn(inputCn, "appearance-none cursor-pointer")}
                            >
                                <option value="">None</option>
                                {categories.map((c) => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                                <option value="__new__">+ New Category</option>
                            </select>
                            {category === '__new__' && (
                                <input
                                    value={newCategory}
                                    onChange={(e) => setNewCategory(e.target.value)}
                                    placeholder="Category name…"
                                    maxLength={100}
                                    className={cn(inputCn, "mt-2")}
                                />
                            )}
                        </div>
                    </div>

                    {/* Row: Deadline + Scheduled Start + Time Estimate */}
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className={labelCn}>
                                <CalendarIcon size={10} className="inline mr-1 -mt-0.5" />
                                Deadline
                            </label>
                            <input
                                type="datetime-local"
                                value={deadline}
                                onChange={(e) => setDeadline(e.target.value)}
                                className={inputCn}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>
                                <CalendarIcon size={10} className="inline mr-1 -mt-0.5" />
                                Start Date
                            </label>
                            <input
                                type="datetime-local"
                                value={scheduledStart}
                                onChange={(e) => setScheduledStart(e.target.value)}
                                className={inputCn}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>
                                <Clock size={10} className="inline mr-1 -mt-0.5" />
                                Time Estimate
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="number"
                                    min={1}
                                    max={14400}
                                    value={estimatedMinutes}
                                    onChange={(e) => setEstimatedMinutes(e.target.value)}
                                    placeholder="0"
                                    className={cn(inputCn, "flex-1")}
                                />
                                <span className={cn("text-xs font-bold shrink-0", "text-slate-600")}>min</span>
                            </div>
                        </div>
                    </div>

                    {/* Tags */}
                    <div>
                        <label className={labelCn}>Tags (comma-separated)</label>
                        <input
                            value={tagsText}
                            onChange={(e) => setTagsText(e.target.value)}
                            placeholder="e.g. study, backend, react"
                            className={inputCn}
                        />
                    </div>

                    {/* Steps */}
                    <div>
                        <label className={labelCn}>Checklist Steps (one per line)</label>
                        <textarea
                            value={stepsText}
                            onChange={(e) => setStepsText(e.target.value)}
                            placeholder={"Read documentation\nBuild prototype\nWrite tests"}
                            rows={4}
                            className={cn(inputCn, "resize-none font-mono text-xs")}
                        />
                    </div>

                    {/* Notes & Meet URL */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className={labelCn}>Notes (additional context)</label>
                            <textarea
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder="Any extra details, links, references…"
                                rows={2}
                                maxLength={10000}
                                className={cn(inputCn, "resize-none")}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>Meeting Link</label>
                            <input
                                value={meetUrl}
                                onChange={(e) => setMeetUrl(e.target.value)}
                                placeholder="https://meet.google.com/..."
                                className={inputCn}
                            />
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className={cn("flex items-center justify-end gap-3 px-6 py-4 border-t", "border-slate-800")}>
                    <button
                        onClick={onClose}
                        className={cn("px-5 py-2.5 rounded-xl font-bold text-sm transition-colors", "text-slate-400 hover:bg-slate-800")}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!title.trim() || submitting}
                        className={cn(
                            "px-6 py-2.5 rounded-xl font-bold text-sm transition-colors flex items-center gap-2",
                            "bg-rose-600 hover:bg-rose-700 text-white disabled:bg-slate-800 disabled:text-slate-600"
                        )}
                    >
                        {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                        CREATE MISSION
                    </button>
                </div>
            </motion.div>
        </motion.div>
    )
}
