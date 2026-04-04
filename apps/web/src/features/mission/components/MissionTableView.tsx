"use client"

import React from 'react'
import {
    AlertTriangle,
    Bot,
    Calendar as CalendarIcon,
    CheckCircle2,
    Trash2,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import {
    type Mission,
    PRIORITY_CONFIG,
    STATUS_CONFIG,
    isOverdue,
    formatDuration,
    formatDeadline,
    getCategoryColor,
} from '@/features/mission/types'

/* ═══════════════════════════════════════════════════════════════════
 * TABLE VIEW — Notion-style spreadsheet
 * ═══════════════════════════════════════════════════════════════════ */

interface MissionTableViewProps {
    missions: Mission[]
    onStatusCycle: (m: Mission) => void
    onDelete: (id: string) => void
    onUpdate: (id: string, data: Partial<Mission>) => void
}

export function MissionTableView({ missions, onStatusCycle, onDelete, onUpdate }: MissionTableViewProps) {
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
