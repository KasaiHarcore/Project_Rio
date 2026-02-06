"use client"

import React from 'react'
import Link from 'next/link'
import { KeyRound, ArrowLeft } from 'lucide-react'
import { PageTransition } from '@/components/layout/page-transition'

export default function RecoveryPage() {
  return (
    <div className="min-h-screen bg-[#F4F9FF] flex items-center justify-center p-6 font-sans overflow-hidden relative">
      {/* Background Ambience */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-blue-400/10 blur-[120px]"></div>

      <PageTransition 
         className="w-full max-w-md bg-white border border-blue-100 rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden z-10"
      >
        
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 border-2 border-blue-100 rounded-full mb-6 relative">
            <KeyRound className="h-8 w-8 text-blue-500 animate-pulse relative z-10" />
            <div className="absolute inset-0 bg-blue-400/20 blur-xl rounded-full"></div>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Link Restoration</h1>
          <p className="text-slate-500 text-sm mt-2 font-medium">Lost your connection? Enter your email to restore the neural link.</p>
        </div>

        <form className="space-y-6">
          <div>
            <label className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] ml-2">Registered Email</label>
            <input type="email" placeholder="sensei@schale.edu" className="w-full px-5 py-4 bg-white border border-blue-100 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-400 transition-all outline-none text-slate-700 placeholder:text-slate-300" />
          </div>
          
          <button className="w-full py-4 bg-blue-500 hover:bg-blue-600 text-white font-black rounded-2xl shadow-xl shadow-blue-100 transition-all active:scale-95 uppercase tracking-widest text-sm">
            Send Reset Link
          </button>
          
          <Link href="/login" className="flex items-center justify-center w-full py-4 bg-white border-2 border-blue-100 text-slate-400 font-black rounded-2xl hover:bg-slate-50 transition-all uppercase tracking-widest text-[10px] group">
            <ArrowLeft className="h-3 w-3 mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Login
          </Link>
        </form>

        <div className="mt-10 border-t border-blue-50 pt-4 flex justify-between items-center opacity-30">
          <span className="text-[9px] font-mono text-blue-400">SECURE_RECOVERY_MODE</span>
          <span className="text-[9px] font-mono text-blue-400">V2.0.6</span>
        </div>
        <div className="mt-10 border-t border-blue-50 pt-4 flex justify-between items-center opacity-30">
          <span className="text-[9px] font-mono text-blue-400">SECURE_RECOVERY_MODE</span>
          <span className="text-[9px] font-mono text-blue-400">V2.0.6</span>
        </div>
      </PageTransition>
    </div>
  )
}
