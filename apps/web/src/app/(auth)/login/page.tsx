"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageTransition } from '@/components/layout/page-transition'

export default function LoginPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

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
    <div className="flex min-h-screen items-center justify-center bg-[#F4F9FF] p-6 font-sans overflow-hidden">
      <PageTransition className="relative w-full max-w-md overflow-hidden rounded-[2.5rem] border border-blue-100 bg-white p-10 shadow-2xl">
        {/* Background Blobs - Matched from HTML */}
        <div className="absolute -top-10 -right-10 h-32 w-32 rounded-full bg-blue-400/10 blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full bg-blue-300/10 blur-3xl"></div>

        <div className="mb-10 text-center relative z-10">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-500 shadow-lg shadow-blue-200">
             {/* System Login Icon from HTML */}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">System Login</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">Please authenticate to access your AI Agent</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5 relative z-10">
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold tracking-widest text-blue-600 uppercase">Email Address</label>
            <input 
                type="email" 
                placeholder="sensei@schale.edu" 
                className="w-full rounded-2xl border border-blue-100 bg-white px-5 py-4 text-slate-700 transition-all outline-none placeholder:text-slate-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                required
            />
          </div>

          <div>
            <div className="mb-2 ml-1 flex justify-between">
              <label className="text-xs font-bold tracking-widest text-blue-600 uppercase">Password</label>
              <Link href="/recovery" className="text-xs font-semibold text-blue-400 transition-colors hover:text-blue-600">Forgot?</Link>
            </div>
            <input 
                type="password" 
                placeholder="••••••••" 
                className="w-full rounded-2xl border border-blue-100 bg-white px-5 py-4 text-slate-700 transition-all outline-none placeholder:text-slate-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                required
            />
          </div>

          <button disabled={isLoading} className="mt-4 w-full transform rounded-2xl bg-blue-500 py-4 font-bold text-white shadow-lg shadow-blue-200 transition-all hover:-translate-y-1 hover:bg-blue-600 active:scale-95 disabled:opacity-70 disabled:hover:translate-y-0">
             {isLoading ? "Authenticating..." : "Connect to Agent"}
          </button>
        </form>

        <div className="mt-10 relative z-10">
          <div className="relative mb-8 flex items-center justify-center">
            <div className="absolute w-full border-t border-blue-50"></div>
            <span className="relative bg-white px-4 text-xs font-bold tracking-tighter text-blue-300 uppercase">Quick Access</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button type="button" className="flex items-center justify-center rounded-xl border border-blue-100 py-3 transition-colors hover:bg-blue-50">
              <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="mr-2 h-5 w-5" alt="Google" />
              <span className="text-sm font-semibold text-slate-600">Google</span>
            </button>
            <button type="button" className="flex items-center justify-center rounded-xl border border-blue-100 py-3 transition-colors hover:bg-blue-50">
              <img src="https://www.svgrepo.com/show/475654/github-color.svg" className="mr-2 h-5 w-5" alt="Github" />
              <span className="text-sm font-semibold text-slate-600">Github</span>
            </button>
          </div>
        </div>

        <p className="text-center mt-8 text-xs font-bold text-slate-400 uppercase tracking-tight">
            New user? <Link href="/register" className="font-bold text-blue-500 hover:underline">Create an ID</Link>
        </p>
      </PageTransition>
    </div>
  )
}
