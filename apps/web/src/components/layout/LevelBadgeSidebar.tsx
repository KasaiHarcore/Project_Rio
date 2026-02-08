"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { useUIStore } from '@/store/ui-store'

export function LevelBadgeSidebar() {
    const { userLevel } = useUIStore()

    return (
        <div id="level-badge" className="relative group cursor-pointer hover:scale-105 transition-transform">
             <div className="w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-lg transition-colors bg-white border-[var(--badge-border)] text-[var(--badge-text)]">
                <span className="font-black font-mono text-lg">{userLevel}</span>
            </div>
            
             {/* Exp Ring (SVG) */}
             <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90 pointer-events-none">
                 <circle
                     cx="28" cy="28" r="26"
                     fill="none"
                     stroke="var(--badge-ring-stroke)"
                     strokeWidth="2"
                    strokeDasharray="163" 
                    strokeDashoffset={40}
                    strokeLinecap="round"
                    className="opacity-80"
                 />
             </svg>
             
             {/* Sensei Label below */}
             <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded text-white shadow-sm whitespace-nowrap bg-[var(--badge-label-bg)]">
                 Sensei
             </div>
        </div>
    )
}
