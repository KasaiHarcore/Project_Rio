"use client"

import React from 'react'
import { AnimatePresence } from 'framer-motion'
import { cn } from '@/shared/lib/utils'
import {
    type Mission,
    type MissionStatus,
    STATUS_CONFIG,
} from '@/features/mission/types'
import { MissionCard } from './MissionCard'

/* ═══════════════════════════════════════════════════════════════════
 * BOARD VIEW — Kanban columns by status
 * ═══════════════════════════════════════════════════════════════════ */

interface MissionBoardViewProps {
    missions: Mission[]
    expandedMission: string | null
    setExpandedMission: (id: string | null) => void
    onStatusCycle: (m: Mission) => void
    onDelete: (id: string) => void
    onToggleStep: (missionId: string, idx: number) => void
    onUpdate: (id: string, data: Partial<Mission>) => void
}

export function MissionBoardView({ missions, expandedMission, setExpandedMission, onStatusCycle, onDelete, onToggleStep, onUpdate }: MissionBoardViewProps) {
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
