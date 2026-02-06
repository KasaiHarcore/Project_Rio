"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { UserPlus, Loader2 } from 'lucide-react'
import { PageTransition } from "@/components/layout/page-transition"

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

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
    <div className="min-h-screen bg-[#F4F9FF] flex items-center justify-center p-6 font-sans relative overflow-hidden">
        {/* Background Ambience */}
      <div className="absolute -top-10 -left-10 h-64 w-64 rounded-full bg-blue-400/20 blur-[100px] animate-pulse"></div>
      <div className="absolute -bottom-10 -right-10 h-80 w-80 rounded-full bg-blue-300/20 blur-[100px] animate-pulse delay-1000"></div>

      <PageTransition 
         className="w-full max-w-md bg-white border border-blue-100 rounded-[2.5rem] shadow-2xl p-10 relative overflow-hidden z-10"
      >
        
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-500 rounded-xl mb-4 text-white shadow-lg shadow-blue-100">
            <UserPlus className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">New Enrollment</h1>
          <p className="text-slate-500 text-sm mt-2 font-medium">Create your Schale Account ID</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] ml-2">Full Name</label>
            <input type="text" placeholder="Sensei Name" className="w-full px-5 py-4 bg-white border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all outline-none text-slate-700 placeholder:text-slate-300" />
          </div>
          <div>
            <label className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] ml-2">Email Address</label>
            <input type="email" placeholder="sensei@schale.edu" className="w-full px-5 py-4 bg-white border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all outline-none text-slate-700 placeholder:text-slate-300" />
          </div>
          <div>
            <label className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] ml-2">Secure Password</label>
            <input type="password" placeholder="••••••••" className="w-full px-5 py-4 bg-white border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all outline-none text-slate-700 placeholder:text-slate-300" />
            <div className="flex mt-2 px-1 space-x-1">
              <div className="h-1 flex-1 bg-blue-400 rounded-full"></div>
              <div className="h-1 flex-1 bg-blue-400 rounded-full"></div>
              <div className="h-1 flex-1 bg-blue-100 rounded-full"></div>
            </div>
          </div>
          <div>
            <label className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] ml-2">Re-typed Password</label>
            <input type="password" placeholder="••••••••" className="w-full px-5 py-4 bg-white border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all outline-none text-slate-700 placeholder:text-slate-300" />
          </div>

            <button disabled={loading} className="w-full py-4 bg-blue-500 hover:bg-blue-600 text-white font-black rounded-2xl shadow-xl shadow-blue-100 mt-8 transition-all active:scale-95 uppercase tracking-widest text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center">
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Initiate Enrollment'}
            </button>
        </form>

        <p className="text-center mt-8 text-xs font-bold text-slate-400 uppercase tracking-tight">
          Already have an ID? <Link href="/login" className="text-blue-500 hover:underline">Log In</Link>
        </p>
      </PageTransition>
    </div>
  )
}
