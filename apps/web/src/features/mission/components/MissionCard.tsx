"use client"

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Bot,
    Calendar as CalendarIcon,
    CheckCircle2,
    Clock,
    Trash2,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import {
    type Mission,
    PRIORITY_CONFIG,
    isOverdue,
    formatDuration,
    formatDeadline,
    deadlineToInputValue,
    getCategoryColor,
} from '@/features/mission/types'

/* ═══════════════════════════════════════════════════════════════════
 * MISSION CARD — Used in Board view
 * ═══════════════════════════════════════════════════════════════════ */

interface MissionCardProps {
    mission: Mission
    expanded: boolean
    onToggleExpand: () => void
    onStatusCycle: () => void
    onDelete: () => void
    onToggleStep: (idx: number) => void
    onUpdate: (data: Partial<Mission>) => void
}

export function MissionCard({ mission, expanded, onToggleExpand, onStatusCycle, onDelete, onToggleStep, onUpdate }: MissionCardProps) {
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
                                    value={deadlineToInputValue(mission.deadline)}
                                    onChange={(e) => onUpdate({ deadline: e.target.value ? new Date(e.target.value).toISOString() : null } as Partial<Mission>)}
                                    className={cn(
                                        "text-xs px-2 py-1 rounded-lg outline-none border",
                                        "bg-slate-900 border-slate-700 text-slate-300"
                                    )}
                                    style={{ colorScheme: 'dark' }}
                                    onClick={(e) => e.stopPropagation()}
                                />
                                {mission.deadline && (
                                    <span className={cn("text-[10px] font-semibold", overdue ? "text-red-500" : "text-slate-400")}>
                                        {formatDeadline(mission.deadline)}
                                    </span>
                                )}
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
