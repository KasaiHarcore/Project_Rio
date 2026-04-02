"use client"

import React from 'react'
import Link from 'next/link'
import { KeyRound, ArrowLeft, ShieldAlert } from 'lucide-react'
import { PageTransition } from '@/components/layout/page-transition'

export default function RecoveryPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 font-sans overflow-hidden relative transition-colors bg-[#0d1117]">
      {/* Background Ambience */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full blur-[120px] bg-rose-900/10"></div>

      <PageTransition
         className="w-full max-w-md border rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden z-10 transition-all bg-[#161b22] border-rose-900/30 shadow-none"
      >

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 border-2 rounded-full mb-6 relative bg-rose-900/10 border-rose-600/30">
            <KeyRound className="h-8 w-8 animate-pulse relative z-10 text-rose-500" />
            <div className="absolute inset-0 blur-xl rounded-full bg-rose-500/20"></div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Account Recovery
          </h1>
          <p className="text-sm mt-2 font-medium text-slate-400">
            Lost access to your account?
          </p>
        </div>

        <div className="space-y-5">
          <div className="rounded-2xl border p-5 space-y-3 bg-[#0d1117] border-rose-900/20">
            <div className="flex items-start gap-3">
              <ShieldAlert className="h-5 w-5 mt-0.5 shrink-0 text-rose-400" />
              <div>
                <p className="text-sm font-semibold mb-1 text-slate-200">
                  Password changes require authentication
                </p>
                <p className="text-xs leading-relaxed text-slate-400">
                  For security, you can only change your password while logged in.
                  Go to <span className="font-semibold">Settings → Security</span> after signing in.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border p-5 space-y-3 bg-[#0d1117] border-rose-900/20">
            <p className="text-sm font-semibold text-slate-200">
              Can&apos;t log in at all?
            </p>
            <p className="text-xs leading-relaxed text-slate-400">
              Contact your system administrator to reset your password manually.
            </p>
          </div>

          <Link
            href="/login"
            className="flex items-center justify-center w-full py-4 border-2 font-black rounded-2xl transition-all uppercase tracking-widest text-[10px] group bg-[#0d1117] border-rose-900/20 text-slate-500 hover:bg-rose-900/10 hover:border-rose-900/40 hover:text-rose-400"
          >
            <ArrowLeft className="h-3 w-3 mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Login
          </Link>
        </div>

        <div className="mt-10 border-t pt-4 flex justify-between items-center opacity-30 border-rose-900/20">
          <span className="text-[9px] font-mono text-rose-400">SECURE_RECOVERY_MODE</span>
          <span className="text-[9px] font-mono text-rose-400">V2.0.6</span>
        </div>
      </PageTransition>
    </div>
  )
}
