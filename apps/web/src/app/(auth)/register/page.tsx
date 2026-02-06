"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { UserPlus, Loader2 } from 'lucide-react'
import { PageTransition } from "@/components/layout/page-transition"
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // Set mock auth cookie
    document.cookie = "auth-token=mock-token-xyz; path=/; max-age=86400"
    
    router.push('/onboarding')
  }

  return (
    <div className={cn("min-h-screen flex items-center justify-center p-6 font-sans relative overflow-hidden transition-colors", isPlana ? "bg-[#0d1117]" : "bg-[#F4F9FF]")}>
        {/* Background Ambience */}
      <div className={cn("absolute -top-10 -left-10 h-64 w-64 rounded-full blur-[100px] animate-pulse", isPlana ? "bg-rose-900/10" : "bg-blue-400/20")}></div>
      <div className={cn("absolute -bottom-10 -right-10 h-80 w-80 rounded-full blur-[100px] animate-pulse delay-1000", isPlana ? "bg-rose-800/10" : "bg-blue-300/20")}></div>

      <PageTransition 
         className={cn(
             "w-full max-w-md border rounded-[2.5rem] p-10 relative overflow-hidden z-10 transition-all",
             isPlana ? "bg-[#161b22] border-rose-900/30 shadow-none" : "bg-white border-blue-100 shadow-2xl"
         )}
      >
        
        <div className="text-center mb-8">
          <div className={cn(
              "inline-flex items-center justify-center w-12 h-12 rounded-xl mb-4 text-white shadow-lg",
              isPlana ? "bg-rose-600 shadow-rose-900/20" : "bg-blue-500 shadow-blue-100"
          )}>
            <UserPlus className="h-6 w-6" />
          </div>
          <h1 className={cn("text-2xl font-bold tracking-tight", isPlana ? "text-slate-100" : "text-slate-800")}>New Enrollment</h1>
          <p className={cn("text-sm mt-2 font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>Create your Schale Account ID</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className={cn("text-[10px] font-black uppercase tracking-[0.2em] ml-2", isPlana ? "text-rose-500" : "text-blue-500")}>Full Name</label>
            <input 
                type="text" 
                placeholder="Sensei Name" 
                className={cn(
                    "w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:ring-blue-100 focus:border-blue-400"
                )} 
            />
          </div>
          <div>
            <label className={cn("text-[10px] font-black uppercase tracking-[0.2em] ml-2", isPlana ? "text-rose-500" : "text-blue-500")}>Email Address</label>
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
          <div>
            <label className={cn("text-[10px] font-black uppercase tracking-[0.2em] ml-2", isPlana ? "text-rose-500" : "text-blue-500")}>Secure Password</label>
            <input 
                type="password" 
                placeholder="••••••••" 
                className={cn(
                    "w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:ring-blue-100 focus:border-blue-400"
                )} 
            />
            <div className="flex mt-2 px-1 space-x-1">
              <div className={cn("h-1 flex-1 rounded-full", isPlana ? "bg-rose-500" : "bg-blue-400")}></div>
              <div className={cn("h-1 flex-1 rounded-full", isPlana ? "bg-rose-500" : "bg-blue-400")}></div>
              <div className={cn("h-1 flex-1 rounded-full", isPlana ? "bg-rose-900/20" : "bg-blue-100")}></div>
            </div>
          </div>
          <div>
            <label className={cn("text-[10px] font-black uppercase tracking-[0.2em] ml-2", isPlana ? "text-rose-500" : "text-blue-500")}>Re-typed Password</label>
            <input 
                type="password" 
                placeholder="••••••••" 
                className={cn(
                    "w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:ring-blue-100 focus:border-blue-400"
                )} 
            />
          </div>

            <button 
                disabled={loading} 
                className={cn(
                    "w-full py-4 text-white font-black rounded-2xl shadow-xl mt-8 transition-all active:scale-95 uppercase tracking-widest text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center",
                    isPlana 
                        ? "bg-rose-600 hover:bg-rose-500 shadow-rose-900/20" 
                        : "bg-blue-500 hover:bg-blue-600 shadow-blue-100"
                )}
            >
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Initiate Enrollment'}
            </button>
        </form>

        <p className={cn("text-center mt-8 text-xs font-bold uppercase tracking-tight", isPlana ? "text-slate-500" : "text-slate-400")}>
          Already have an ID? <Link href="/login" className={cn("hover:underline", isPlana ? "text-rose-500" : "text-blue-500")}>Log In</Link>
        </p>
      </PageTransition>
    </div>
  )
}
