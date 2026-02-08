"use client"

import React from 'react'
import { Bell, Coins, Zap } from 'lucide-react'
import { useUIStore } from '@/store/ui-store'

export function Header() {
    const { userLevel, currentAp, maxAp, credits } = useUIStore()

    return (
        <header 
            id="schale-header"
            className="h-14 md:h-16 w-full flex items-center justify-between px-3 md:px-6 z-30 transition-colors duration-300 bg-gradient-to-b to-transparent"
            style={{ '--tw-gradient-from': 'var(--header-gradient-from)' } as React.CSSProperties}
        >
            {/* Left: Page Context */}
            <div className="flex items-center gap-4">
                <LevelBadge level={userLevel} />
                <div className="flex flex-col">
                    <span className="text-xs font-bold uppercase tracking-widest text-[var(--header-subtitle)]">
                        Sensei
                    </span>
                    <span className="text-sm font-black tracking-wide text-[var(--header-name)]">
                        S.C.H.A.L.E Office
                    </span>
                </div>
            </div>

            {/* Right: Resources & System Status */}
            <div className="flex items-center gap-3 md:gap-6">
                
                {/* AP / Stamina Bar - Hidden on small screens */}
                <div className="hidden md:block">
                    <ResourceDisplay 
                        icon={<Zap size={16} className="text-[var(--header-ap-icon)]" fill="currentColor" />}
                        value={`${currentAp}/${maxAp}`}
                        label="AP"
                    />
                </div>

                {/* Credits - Hidden on small screens */}
                <div className="hidden md:block">
                    <ResourceDisplay 
                        icon={<Coins size={16} className="text-[var(--header-credits-icon)]" />}
                        value={credits.toLocaleString()}
                        label="CREDITS"
                    />
                </div>

                {/* Compact mobile resource display */}
                <div className="flex md:hidden items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-md text-xs font-bold bg-[var(--header-resource-bg)] border-[var(--header-resource-border)] text-[var(--header-resource-text)]">
                    <Zap size={12} className="text-[var(--header-ap-icon)]" fill="currentColor" />
                    <span className="font-mono">{currentAp}</span>
                </div>

                {/* Vertical Divider */}
                <div className="h-6 w-[1px] bg-slate-200/50 hidden md:block" />

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

function LevelBadge({ level }: { level: number }) {
    return (
        <div id="level-badge" className="relative group cursor-pointer">
            <div className="w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors border-[var(--header-level-border)] bg-[var(--header-level-bg)] text-[var(--header-level-text)]">
                <span className="font-black font-mono text-lg">{level}</span>
            </div>
            {/* Exp Ring (SVG) */}
            <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90 pointer-events-none">
                 <circle
                     cx="28" cy="28" r="26"
                     fill="none"
                     stroke="var(--header-level-ring)"
                     strokeWidth="2"
                    strokeDasharray="163" 
                    strokeDashoffset={40}
                    strokeLinecap="round"
                    className="opacity-80"
                 />
             </svg>
        </div>
    )
}

function ResourceDisplay({ icon, value, label }: { icon: React.ReactNode, value: string, label: string }) {
    return (
        <div className="flex items-center h-9 px-4 rounded-full border backdrop-blur-md shadow-sm gap-3 min-w-[140px] bg-[var(--header-resource-bg)] border-[var(--header-resource-border)] text-[var(--header-resource-text)]">
            {icon}
            <div className="flex flex-col items-end flex-1 leading-none">
                 <span className="font-mono font-bold text-sm tracking-tighter">{value}</span>
            </div>
            <div className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold text-white bg-[var(--header-resource-badge)]">
                +
            </div>
        </div>
    )
}
