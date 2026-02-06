"use client"

import React from 'react'
import Link from 'next/link'
import { KeyRound, ArrowLeft } from 'lucide-react'
import { PageTransition } from '@/components/layout/page-transition'
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

export default function RecoveryPage() {
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  return (
    <div className={cn("min-h-screen flex items-center justify-center p-6 font-sans overflow-hidden relative transition-colors", isPlana ? "bg-[#0d1117]" : "bg-[#F4F9FF]")}>
      {/* Background Ambience */}
      <div className={cn("absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full blur-[120px]", isPlana ? "bg-rose-900/10" : "bg-blue-400/10")}></div>

      <PageTransition 
         className={cn(
             "w-full max-w-md border rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden z-10 transition-all",
             isPlana ? "bg-[#161b22] border-rose-900/30 shadow-none" : "bg-white border-blue-100"
         )}
      >
        
        <div className="text-center mb-8">
          <div className={cn(
              "inline-flex items-center justify-center w-16 h-16 border-2 rounded-full mb-6 relative",
              isPlana ? "bg-rose-900/10 border-rose-600/30" : "bg-blue-50 border-blue-100"
          )}>
            <KeyRound className={cn("h-8 w-8 animate-pulse relative z-10", isPlana ? "text-rose-500" : "text-blue-500")} />
            <div className={cn("absolute inset-0 blur-xl rounded-full", isPlana ? "bg-rose-500/20" : "bg-blue-400/20")}></div>
          </div>
          <h1 className={cn("text-2xl font-bold tracking-tight", isPlana ? "text-slate-100" : "text-slate-800")}>Link Restoration</h1>
          <p className={cn("text-sm mt-2 font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>Lost your connection? Enter your email to restore the neural link.</p>
        </div>

        <form className="space-y-6">
          <div>
            <label className={cn("text-[10px] font-black uppercase tracking-[0.2em] ml-2", isPlana ? "text-rose-500" : "text-blue-500")}>Registered Email</label>
            <input 
                type="email" 
                placeholder="sensei@schale.edu" 
                className={cn(
                    "w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:ring-blue-100 focus:border-blue-400"
                )}
            />
          </div>
          
          <button className={cn(
              "w-full py-4 text-white font-black rounded-2xl shadow-xl transition-all active:scale-95 uppercase tracking-widest text-sm",
              isPlana ? "bg-rose-600 hover:bg-rose-500 shadow-rose-900/20" : "bg-blue-500 hover:bg-blue-600 shadow-blue-100"
          )}>
            Send Reset Link
          </button>
          
          <Link 
            href="/login" 
            className={cn(
                "flex items-center justify-center w-full py-4 border-2 font-black rounded-2xl transition-all uppercase tracking-widest text-[10px] group",
                isPlana 
                    ? "bg-[#0d1117] border-rose-900/20 text-slate-500 hover:bg-rose-900/10 hover:border-rose-900/40 hover:text-rose-400" 
                    : "bg-white border-blue-100 text-slate-400 hover:bg-slate-50"
            )}
          >
            <ArrowLeft className="h-3 w-3 mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Login
          </Link>
        </form>

        <div className={cn("mt-10 border-t pt-4 flex justify-between items-center opacity-30", isPlana ? "border-rose-900/20" : "border-blue-50")}>
          <span className={cn("text-[9px] font-mono", isPlana ? "text-rose-400" : "text-blue-400")}>SECURE_RECOVERY_MODE</span>
          <span className={cn("text-[9px] font-mono", isPlana ? "text-rose-400" : "text-blue-400")}>V2.0.6</span>
        </div>
      </PageTransition>
    </div>
  )
}
