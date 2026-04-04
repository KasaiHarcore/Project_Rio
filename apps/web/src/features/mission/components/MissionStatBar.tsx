"use client"

import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
    Filter,
    Kanban,
    Calendar as CalendarIcon,
    Plus,
    Table2,
    Trophy,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { MissionPriority } from '@/features/mission/types'

/* ═══════════════════════════════════════════════════════════════════
 * StatPill — single stat value in the stats bar
 * ═══════════════════════════════════════════════════════════════════ */

export function StatPill({ label, value, alert }: { label: string; value: number; alert?: boolean }) {
    return (
        <div className={cn("flex flex-col items-center", alert && "text-yellow-200")}>
            <span className={cn("text-xl font-black", alert && "text-yellow-200")}>{value}</span>
            <span className="text-[10px] font-bold opacity-60 uppercase">{label}</span>
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════════════
 * ViewSwitcher — board / table / calendar toggle
 * ═══════════════════════════════════════════════════════════════════ */

export function ViewSwitcher({ viewMode, setViewMode }: {
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

/* ═══════════════════════════════════════════════════════════════════
 * TabButton — active / done / all tab
 * ═══════════════════════════════════════════════════════════════════ */

export function TabButton({ active, onClick, label, count }: {
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
 * StatsBar — progress overview + "New Mission" button
 * ═══════════════════════════════════════════════════════════════════ */

export function StatsBar({ overallProgress, totalActive, totalCompleted, totalOverdue, onCreateClick }: {
    overallProgress: number
    totalActive: number
    totalCompleted: number
    totalOverdue: number
    onCreateClick: () => void
}) {
    return (
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
                    onClick={onCreateClick}
                    className="px-5 py-2.5 bg-white/20 hover:bg-white/30 rounded-xl font-bold text-sm flex items-center gap-2 transition-colors backdrop-blur-sm"
                >
                    <Plus size={16} /> New Mission
                </button>
            </div>
            <Trophy className="absolute -bottom-8 -right-8 w-36 h-36 opacity-[0.08] rotate-12" />
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════════════
 * FilterBar — category + priority filter pills
 * ═══════════════════════════════════════════════════════════════════ */

export function FilterBar({
    showFilters, setShowFilters,
    filterCategory, setFilterCategory,
    filterPriority, setFilterPriority,
    categories,
}: {
    showFilters: boolean
    setShowFilters: (v: boolean) => void
    filterCategory: string | null
    setFilterCategory: (v: string | null) => void
    filterPriority: MissionPriority | null
    setFilterPriority: (v: MissionPriority | null) => void
    categories: string[]
}) {
    return (
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
                                <option className="bg-[#1e293b] text-[#cbd5e1]" value="">All Categories</option>
                                {categories.map((c) => (
                                    <option className="bg-[#1e293b] text-[#cbd5e1]" key={c} value={c}>{c}</option>
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
                            <option className="bg-[#1e293b] text-[#cbd5e1]" value="">All Priorities</option>
                            <option className="bg-[#1e293b] text-[#cbd5e1]" value="critical">🔴 Critical</option>
                            <option className="bg-[#1e293b] text-[#cbd5e1]" value="normal">🔵 Normal</option>
                            <option className="bg-[#1e293b] text-[#cbd5e1]" value="low">⚪ Low</option>
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
    )
}
