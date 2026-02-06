"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { Bell, Coins, Zap } from 'lucide-react'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'

export function Header() {
    const { userLevel, currentAp, maxAp, credits, activeCharacterId } = useUIStore()
    const isPlana = activeCharacterId === 'plana'

    return (
        <header 
            id="schale-header"
            className={cn(
                "h-16 w-full flex items-center justify-between px-6 z-30 transition-colors duration-300",
                "bg-gradient-to-b from-white/80 to-transparent",
                isPlana && "from-[#1a1625]/80" 
            )}
        >
            {/* Left: Page Context */}
            <div className="flex items-center gap-4">
                <LevelBadge level={userLevel} isPlana={isPlana} />
                <div className="flex flex-col">
                    <span className={cn("text-xs font-bold uppercase tracking-widest", isPlana ? "text-slate-400" : "text-slate-500")}>
                        Sensei
                    </span>
                    <span className={cn("text-sm font-black tracking-wide", isPlana ? "text-white" : "text-slate-700")}>
                        S.C.H.A.L.E Office
                    </span>
                </div>
            </div>

            {/* Right: Resources & System Status */}
            <div className="flex items-center gap-6">
                
                {/* AP / Stamina Bar */}
                <ResourceDisplay 
                    icon={<Zap size={16} className={isPlana ? "text-rose-400" : "text-yellow-500"} fill="currentColor" />}
                    value={`${currentAp}/${maxAp}`}
                    label="AP"
                    isPlana={isPlana}
                />

                {/* Credits */}
                <ResourceDisplay 
                    icon={<Coins size={16} className={isPlana ? "text-slate-300" : "text-slate-500"} />}
                    value={credits.toLocaleString()}
                    label="CREDITS"
                    isPlana={isPlana}
                />

                {/* Vertical Divider */}
                <div className="h-6 w-[1px] bg-slate-200/50" />

                {/* Notifications */}
                <button className={cn(
                    "relative p-2 rounded-full transition-colors hover:bg-black/5",
                    isPlana ? "text-slate-300 hover:bg-white/10" : "text-slate-600"
                )}>
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                </button>
            </div>
        </header>
    )
}

function LevelBadge({ level, isPlana }: { level: number, isPlana: boolean }) {
    return (
        <div id="level-badge" className="relative group cursor-pointer">
            <div className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors border-[#1289F4] bg-white text-[#1289F4]",
                isPlana && "border-rose-500 bg-[#2d253a] text-rose-500"
            )}>
                <span className="font-black font-mono text-lg">{level}</span>
            </div>
            {/* Exp Ring (SVG) */}
            <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90 pointer-events-none">
                 <circle
                     cx="28" cy="28" r="26"
                     fill="none"
                     stroke={isPlana ? "#f43f5e" : "#1289F4"}
                     strokeWidth="2"
                    strokeDasharray="163" 
                    strokeDashoffset={40} // 75% full
                    strokeLinecap="round"
                    className="opacity-80"
                 />
             </svg>
        </div>
    )
}

function ResourceDisplay({ icon, value, label, isPlana }: { icon: React.ReactNode, value: string, label: string, isPlana: boolean }) {
    return (
        <div className={cn(
            "flex items-center h-9 px-4 rounded-full border bg-white/60 backdrop-blur-md shadow-sm gap-3 min-w-[140px]",
            isPlana ? "bg-[#2d253a]/80 border-white/10 text-slate-200" : "border-[#1289F4]/20 text-slate-700"
        )}>
            {icon}
            <div className="flex flex-col items-end flex-1 leading-none">
                 <span className="font-mono font-bold text-sm tracking-tighter">{value}</span>
            </div>
            <div className={cn(
                "w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold text-white",
                isPlana ? "bg-slate-600" : "bg-[#1289F4]"
            )}>
                +
            </div>
        </div>
    )
}
