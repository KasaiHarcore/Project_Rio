"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageTransition } from '@/components/layout/page-transition'
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

export default function LoginPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const { theme } = useTheme()
  const isPlana = theme === 'dark'

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    // Simulate login delay
    setTimeout(() => {
        document.cookie = "auth-token=mock-token; path=/; max-age=86400"
        router.push('/')
        router.refresh()
    }, 1500)
  }

  return (
    <div className={cn("flex min-h-screen items-center justify-center p-6 font-sans overflow-hidden transition-colors", isPlana ? "bg-[#0d1117]" : "bg-[#F4F9FF]")}>
      <PageTransition className={cn(
          "relative w-full max-w-md overflow-hidden rounded-[2.5rem] border p-10 shadow-2xl transition-all",
          isPlana ? "bg-[#161b22] border-rose-900/30 shadow-rose-900/10" : "bg-white border-blue-100"
      )}>
        {/* Background Blobs */}
        <div className={cn("absolute -top-10 -right-10 h-32 w-32 rounded-full blur-3xl", isPlana ? "bg-rose-900/10" : "bg-blue-400/10")}></div>
        <div className={cn("absolute -bottom-10 -left-10 h-40 w-40 rounded-full blur-3xl", isPlana ? "bg-rose-900/10" : "bg-blue-300/10")}></div>

        <div className="mb-10 text-center relative z-10">
          <div className={cn(
              "mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg transition-colors",
              isPlana ? "bg-rose-600 shadow-rose-900/40" : "bg-blue-500 shadow-blue-200"
          )}>
             {/* System Login Icon */}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
            </svg>
          </div>
          <h1 className={cn("text-2xl font-bold tracking-tight", isPlana ? "text-slate-100" : "text-slate-800")}>System Login</h1>
          <p className={cn("mt-2 text-sm font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>Please authenticate to access your AI Agent</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5 relative z-10">
          <div>
            <label className={cn("mb-2 ml-1 block text-xs font-bold tracking-widest uppercase", isPlana ? "text-rose-400" : "text-blue-600")}>Email Address</label>
            <input 
                type="email" 
                placeholder="sensei@schale.edu" 
                className={cn(
                    "w-full rounded-2xl border px-5 py-4 transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-slate-200 placeholder:text-slate-600 focus:border-rose-500 focus:ring-rose-900/20" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:border-blue-400 focus:ring-blue-100"
                )}
                required
            />
          </div>

          <div>
            <div className="mb-2 ml-1 flex justify-between">
              <label className={cn("text-xs font-bold tracking-widest uppercase", isPlana ? "text-rose-400" : "text-blue-600")}>Password</label>
              <Link href="/recovery" className={cn("text-xs font-semibold transition-colors", isPlana ? "text-slate-500 hover:text-rose-400" : "text-blue-400 hover:text-blue-600")}>Forgot?</Link>
            </div>
            <input 
                type="password" 
                placeholder="••••••••" 
                className={cn(
                    "w-full rounded-2xl border px-5 py-4 transition-all outline-none focus:ring-4",
                    isPlana 
                        ? "bg-[#0d1117] border-rose-900/30 text-slate-200 placeholder:text-slate-600 focus:border-rose-500 focus:ring-rose-900/20" 
                        : "bg-white border-blue-100 text-slate-700 placeholder:text-slate-300 focus:border-blue-400 focus:ring-blue-100"
                )}
                required
            />
          </div>

          <button disabled={isLoading} className={cn(
              "mt-4 w-full transform rounded-2xl py-4 font-bold text-white shadow-lg transition-all hover:-translate-y-1 active:scale-95 disabled:opacity-70 disabled:hover:translate-y-0",
              isPlana 
                  ? "bg-rose-600 hover:bg-rose-500 shadow-rose-900/20" 
                  : "bg-blue-500 hover:bg-blue-600 shadow-blue-200"
          )}>
             {isLoading ? "Authenticating..." : "Connect to Agent"}
          </button>
        </form>

        <div className="mt-10 relative z-10">
          <div className="relative mb-8 flex items-center justify-center">
            <div className={cn("absolute w-full border-t", isPlana ? "border-rose-900/20" : "border-blue-50")}></div>
            <span className={cn("relative px-4 text-xs font-bold tracking-tighter uppercase", isPlana ? "bg-[#161b22] text-rose-900/50" : "bg-white text-blue-300")}>Quick Access</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button type="button" className={cn(
                "flex items-center justify-center rounded-xl border py-3 transition-colors",
                isPlana 
                    ? "border-rose-900/20 hover:bg-rose-900/10 text-slate-400" 
                    : "border-blue-100 hover:bg-blue-50 text-slate-600"
            )}>
              <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="mr-2 h-5 w-5" alt="Google" />
              <span className="text-sm font-semibold">Google</span>
            </button>
            <button type="button" className={cn(
                "flex items-center justify-center rounded-xl border py-3 transition-colors",
                isPlana 
                    ? "border-rose-900/20 hover:bg-rose-900/10 text-slate-400" 
                    : "border-blue-100 hover:bg-blue-50 text-slate-600"
            )}>
              <img src="https://www.svgrepo.com/show/475654/github-color.svg" className="mr-2 h-5 w-5" alt="Github" />
              <span className="text-sm font-semibold">Github</span>
            </button>
          </div>
        </div>

        <p className={cn("text-center mt-8 text-xs font-bold uppercase tracking-tight", isPlana ? "text-slate-500" : "text-slate-400")}>
            New user? <Link href="/register" className={cn("font-bold hover:underline", isPlana ? "text-rose-500" : "text-blue-500")}>Create an ID</Link>
        </p>
      </PageTransition>
    </div>
  )
}
