"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LogIn, Github, Mail } from 'lucide-react'
import { motion } from 'framer-motion'

export default function LoginPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    // Simulate login delay
    setTimeout(() => {
        // Set a mock auth cookie
        document.cookie = "auth-token=mock-token; path=/; max-age=86400" // 1 day
        router.push('/')
        router.refresh() // Force refresh to update middleware state
    }, 1500)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F9FF] p-6 font-sans relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute -top-10 -right-10 h-64 w-64 rounded-full bg-blue-400/20 blur-[100px] animate-pulse"></div>
      <div className="absolute -bottom-10 -left-10 h-80 w-80 rounded-full bg-blue-300/20 blur-[100px] animate-pulse delay-1000"></div>

      <motion.div 
         initial={{ opacity: 0, scale: 0.95 }}
         animate={{ opacity: 1, scale: 1 }}
         transition={{ duration: 0.5 }}
         className="relative w-full max-w-md overflow-hidden rounded-[2.5rem] border border-blue-100 bg-white p-10 shadow-2xl z-10"
      >
        <div className="mb-10 text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-500 shadow-lg shadow-blue-200">
            <LogIn className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">System Login</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">Please authenticate to access your AI Agent</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
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
              <Link href="/recovery" className="text-xs font-semibold text-blue-400 transition-colors hover:text-blue-600">
                Forgot?
              </Link>
            </div>
            <input 
                type="password" 
                placeholder="••••••••" 
                className="w-full rounded-2xl border border-blue-100 bg-white px-5 py-4 text-slate-700 transition-all outline-none placeholder:text-slate-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100" 
                required
            />
          </div>

          <button 
             disabled={isLoading}
             className="w-full mt-4 flex items-center justify-center transform rounded-2xl bg-blue-500 py-4 font-bold text-white shadow-lg shadow-blue-200 transition-all hover:bg-blue-600 hover:-translate-y-1 active:scale-95 disabled:opacity-70 disabled:hover:translate-y-0 disabled:active:scale-100"
          >
            {isLoading ? (
                <span className="flex items-center">
                    <span className="animate-spin mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                    Authenticating...
                </span>
            ) : "Connect to Agent"}
          </button>
        </form>

        <div className="mt-10">
          <div className="relative mb-8 flex items-center justify-center">
            <div className="absolute w-full border-t border-blue-50"></div>
            <span className="relative bg-white px-4 text-xs font-bold tracking-tighter text-blue-300 uppercase">Quick Access</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button className="flex items-center justify-center rounded-xl border border-blue-100 py-3 transition-colors hover:bg-blue-50">
               {/* Using generic icons for legal safety vs SVGs from template */}
              <Mail className="mr-2 h-5 w-5 text-slate-600" />
              <span className="text-sm font-semibold text-slate-600">Google</span>
            </button>
            <button className="flex items-center justify-center rounded-xl border border-blue-100 py-3 transition-colors hover:bg-blue-50">
              <Github className="mr-2 h-5 w-5 text-slate-600" />
              <span className="text-sm font-semibold text-slate-600">Github</span>
            </button>
          </div>
        </div>

        <p className="mt-10 text-center text-sm font-medium text-slate-400">
            New user? <Link href="/register" className="font-bold text-blue-500 hover:underline">Create an ID</Link>
        </p>
      </motion.div>
    </div>
  )
}
