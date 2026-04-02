"use client"

import React, { useEffect, useState, useCallback } from 'react'
import { Bell } from 'lucide-react'
import { apiGetDashboardStats, DashboardStats } from '@/features/dashboard/api'

export function Header() {
    const [stats, setStats] = useState<DashboardStats | null>(null)

    const fetchStats = useCallback(async () => {
        try {
            const data = await apiGetDashboardStats()
            setStats(data)
        } catch { /* silent */ }
    }, [])

    useEffect(() => { fetchStats() }, [fetchStats])

    const level = stats?.level ?? 1
    const xpInLevel = stats?.xp_in_level ?? 0
    const xpForNext = stats?.xp_for_next ?? 100

    return (
        <header 
            id="schale-header"
            className="h-14 md:h-16 w-full flex items-center justify-between px-3 md:px-6 z-30 transition-colors duration-300 bg-gradient-to-b to-transparent"
            style={{ '--tw-gradient-from': 'var(--header-gradient-from)' } as React.CSSProperties}
        >
            {/* Left: Level Badge + Identity */}
            <div className="flex items-center gap-4">
                <LevelBadge level={level} progress={xpForNext > 0 ? xpInLevel / xpForNext : 0} />
                <div className="flex flex-col">
                    <span className="text-xs font-bold uppercase tracking-widest text-[var(--header-subtitle)]">
                        Sensei
                    </span>
                    <span className="text-sm font-black tracking-wide text-[var(--header-name)]">
                        S.C.H.A.L.E Office
                    </span>
                </div>
            </div>

            {/* Right: XP info + Notifications */}
            <div className="flex items-center gap-3 md:gap-6">
                {/* XP Progress Pill */}
                <div className="hidden md:flex items-center gap-2 px-4 py-1.5 rounded-full border backdrop-blur-md text-xs font-bold bg-[var(--header-resource-bg)] border-[var(--header-resource-border)] text-[var(--header-resource-text)]">
                    <span className="font-mono">{xpInLevel} / {xpForNext} XP</span>
                    <div className="w-16 h-1.5 rounded-full overflow-hidden bg-slate-200/30">
                        <div
                            className="h-full rounded-full bg-[var(--header-level-ring)] transition-all duration-500"
                            style={{ width: `${xpForNext > 0 ? (xpInLevel / xpForNext) * 100 : 0}%` }}
                        />
                    </div>
                </div>

                {/* Notifications */}
                <button 
                    className="relative p-2 rounded-full transition-colors text-[var(--header-bell-text)] hover:bg-[var(--header-bell-hover)]"
                    aria-label="Notifications"
                >
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" aria-hidden="true" />
                </button>
            </div>
        </header>
    )
}

function LevelBadge({ level, progress }: { level: number; progress: number }) {
    // SVG ring: circumference = 2π × 26 ≈ 163.36
    const circumference = 163.36
    const offset = circumference * (1 - Math.min(progress, 1))

    return (
        <div id="level-badge" className="relative group cursor-pointer">
            <div className="w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors border-[var(--header-level-border)] bg-[var(--header-level-bg)] text-[var(--header-level-text)]">
                <span className="font-black font-mono text-lg">{level}</span>
            </div>
            {/* Exp Ring (SVG) */}
            <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90 pointer-events-none">
                {/* Track */}
                <circle
                    cx="28" cy="28" r="26"
                    fill="none"
                    stroke="var(--header-level-ring)"
                    strokeWidth="2"
                    strokeDasharray={circumference}
                    strokeDashoffset={0}
                    className="opacity-20"
                />
                {/* Progress */}
                <circle
                    cx="28" cy="28" r="26"
                    fill="none"
                    stroke="var(--header-level-ring)"
                    strokeWidth="2"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    className="opacity-80 transition-all duration-700"
                />
            </svg>
        </div>
    )
}
