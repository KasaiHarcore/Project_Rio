"use client"

import React, { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { apiGetDashboardStats, DashboardStats } from '@/lib/api'

export function LevelBadgeSidebar() {
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
    const progress = xpForNext > 0 ? xpInLevel / xpForNext : 0

    // SVG ring: circumference = 2π × 26 ≈ 163.36
    const circumference = 163.36
    const offset = circumference * (1 - Math.min(progress, 1))

    return (
        <div id="level-badge" className="relative group cursor-pointer hover:scale-105 transition-transform">
             <div className="w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors bg-white border-[var(--badge-border)] text-[var(--badge-text)]">
                <span className="font-black font-mono text-lg">{level}</span>
            </div>
            
             {/* Exp Ring (SVG) */}
             <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90 pointer-events-none">
                 {/* Track */}
                 <circle
                     cx="28" cy="28" r="26"
                     fill="none"
                     stroke="var(--badge-ring-stroke)"
                     strokeWidth="2"
                     strokeDasharray={circumference}
                     strokeDashoffset={0}
                     className="opacity-20"
                 />
                 {/* Progress */}
                 <circle
                     cx="28" cy="28" r="26"
                     fill="none"
                     stroke="var(--badge-ring-stroke)"
                     strokeWidth="2"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    className="opacity-80 transition-all duration-700"
                 />
             </svg>
             
             {/* Sensei Label below */}
             <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded text-white shadow-sm whitespace-nowrap bg-[var(--badge-label-bg)]">
                 Lv.{level}
             </div>
        </div>
    )
}
