"use client"

import React from 'react'
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

export function ChatHeader() {
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  return (
    <header className={cn(
        "relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 transition-colors",
        isPlana ? "bg-[#0d1117]/60 border-rose-900/20" : "bg-white/40 border-blue-100"
    )}>
      <div className={cn(
          "absolute bottom-0 left-0 h-[1px] w-full bg-gradient-to-r opacity-50",
          isPlana ? "from-transparent via-rose-600 to-transparent" : "from-transparent via-blue-300 to-transparent"
      )}></div>

      <div className="flex items-center gap-6">
        <div className={cn(
            "flex items-center rounded-lg border px-4 py-1.5 shadow-sm transition-colors",
            isPlana ? "bg-[#161b22] border-rose-900/30" : "bg-white/60 border-blue-100"
        )}>
          <div className={cn(
              "mr-3 h-2 w-2 rounded-full shadow-[0_0_8px]", 
              isPlana ? "bg-rose-500 shadow-rose-900/50" : "bg-emerald-500 shadow-emerald-500/50"
          )}></div>
          <span className={cn("font-mono text-[10px] font-bold uppercase", isPlana ? "text-slate-400" : "text-slate-600")}>System: <span className={cn(isPlana ? "text-rose-500" : "text-emerald-600")}>Stable</span></span>
        </div>
        <div className={cn("h-4 w-[1px]", isPlana ? "bg-slate-700/50" : "bg-slate-300/50")}></div>
        <span className={cn("font-mono text-[10px]", isPlana ? "text-slate-500" : "text-slate-400")}>LATENCY: 24ms</span>
      </div>

      <div className="flex items-center gap-3">
        <button className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg transition-all",
            isPlana 
                ? "text-slate-500 hover:bg-[#161b22] hover:text-rose-400" 
                : "text-slate-400 hover:bg-white hover:text-blue-500"
        )}>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        </button>
        <button className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg transition-all",
            isPlana 
                ? "text-slate-500 hover:bg-[#161b22] hover:text-rose-400" 
                : "text-slate-400 hover:bg-white hover:text-blue-500"
        )}>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </header>
  )
}
