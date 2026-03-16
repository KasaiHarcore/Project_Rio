"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { PageTransition } from '@/components/layout/page-transition'
import { cn } from '@/shared/lib/utils'
import { apiLogin, setTokens } from '@/features/auth/api'

export default function LoginPage() {
  return (
    <React.Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-[#0d1117] text-slate-400">Loading...</div>}>
      <LoginContent />
    </React.Suspense>
  )
}

function LoginContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const res = await apiLogin(email, password)
      setTokens(res.tokens.access_token, res.tokens.refresh_token)
      const next = searchParams.get('next') || '/'
      router.push(next)
      router.refresh()
    } catch (err: any) {
      setError(err?.message || 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6 font-sans overflow-hidden transition-colors bg-[#0d1117]">
      <PageTransition className="relative w-full max-w-md overflow-hidden rounded-[2.5rem] border p-10 shadow-2xl transition-all bg-[#161b22] border-rose-900/30 shadow-rose-900/10">
        {/* Background Blobs */}
        <div className="absolute -top-10 -right-10 h-32 w-32 rounded-full blur-3xl bg-rose-900/10"></div>
        <div className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full blur-3xl bg-rose-900/10"></div>

        <div className="mb-10 text-center relative z-10">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg transition-colors bg-rose-600 shadow-rose-900/40">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">System Login</h1>
          <p className="mt-2 text-sm font-medium text-slate-400">Please authenticate to access your AI Agent</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5 relative z-10">
          {error && (
            <div className="rounded-xl px-4 py-3 text-sm font-medium bg-rose-900/30 text-rose-300">
              {error}
            </div>
          )}
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold tracking-widest uppercase text-rose-400">Email Address</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="sensei@schale.edu"
              className="w-full rounded-2xl border px-5 py-4 transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-slate-200 placeholder:text-slate-600 focus:border-rose-500 focus:ring-rose-900/20"
              required
            />
          </div>

          <div>
            <div className="mb-2 ml-1 flex justify-between">
              <label className="text-xs font-bold tracking-widest uppercase text-rose-400">Password</label>
              <Link href="/recovery" className="text-xs font-semibold transition-colors text-slate-500 hover:text-rose-400">Forgot?</Link>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-2xl border px-5 py-4 transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-slate-200 placeholder:text-slate-600 focus:border-rose-500 focus:ring-rose-900/20"
              required
            />
          </div>

          <button disabled={isLoading} className="mt-4 w-full transform rounded-2xl py-4 font-bold text-white shadow-lg transition-all hover:-translate-y-1 active:scale-95 disabled:opacity-70 disabled:hover:translate-y-0 bg-rose-600 hover:bg-rose-500 shadow-rose-900/20">
            {isLoading ? "Authenticating..." : "Connect to Agent"}
          </button>
        </form>

        <div className="mt-10 relative z-10">
          <div className="relative mb-8 flex items-center justify-center">
            <div className="absolute w-full border-t border-rose-900/20"></div>
            <span className="relative px-4 text-xs font-bold tracking-tighter uppercase bg-[#161b22] text-rose-900/50">Quick Access</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button type="button" className="flex items-center justify-center rounded-xl border py-3 transition-colors border-rose-900/20 hover:bg-rose-900/10 text-slate-400">
              <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="mr-2 h-5 w-5" alt="Google" />
              <span className="text-sm font-semibold">Google</span>
            </button>
            <button type="button" className="flex items-center justify-center rounded-xl border py-3 transition-colors border-rose-900/20 hover:bg-rose-900/10 text-slate-400">
              <img src="https://www.svgrepo.com/show/475654/github-color.svg" className="mr-2 h-5 w-5" alt="Github" />
              <span className="text-sm font-semibold">Github</span>
            </button>
          </div>
        </div>

        <p className="text-center mt-8 text-xs font-bold uppercase tracking-tight text-slate-500">
          New user? <Link href="/register" className="font-bold hover:underline text-rose-500">Create an ID</Link>
        </p>
      </PageTransition>
    </div>
  )
}
