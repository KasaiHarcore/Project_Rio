"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'

export function LevelBadgeSidebar() {
    const { userLevel, activeCharacterId } = useUIStore()
    const isPlana = activeCharacterId === 'plana'

    return (
        <div id="level-badge" className="relative group cursor-pointer hover:scale-105 transition-transform">
             <div className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors bg-white",
                // Blue Archive Style: Blue text for level
                isPlana ? "border-rose-500 text-rose-500" : "border-[#1289F4] text-[#1289F4]"
            )}>
                <span className="font-black font-mono text-lg">{userLevel}</span>
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
                    className="opacity-80 drop-shadow-[0_0_2px_rgba(18,137,244,0.5)]"
                 />
             </svg>
             
             {/* Sensei Label below */}
             <div className={cn(
                 "absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded text-white shadow-sm whitespace-nowrap",
                 isPlana ? "bg-rose-500" : "bg-[#1289F4]"
             )}>
                 Sensei
             </div>
        </div>
    )
}
