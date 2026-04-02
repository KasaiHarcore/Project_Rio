"use client"

import React, { useState, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { UserPlus, Loader2, Check, X } from 'lucide-react'
import { PageTransition } from "@/components/layout/page-transition"
import { cn } from '@/shared/lib/utils'
import { apiRegister, setTokens } from '@/features/auth/api'

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const passwordRules = useMemo(() => {
    const rules = [
      { label: 'At least 12 characters', met: password.length >= 12 },
      { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
      { label: 'One lowercase letter', met: /[a-z]/.test(password) },
      { label: 'One number', met: /[0-9]/.test(password) },
      { label: 'One special character (!@#$...)', met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(password) },
    ]
    const score = rules.filter(r => r.met).length
    const phase: 0 | 1 | 2 | 3 = password.length === 0 ? 0 : score <= 2 ? 1 : score <= 4 ? 2 : 3
    return { rules, score, phase }
  }, [password])

  const strengthLabel = ['', 'Weak', 'Medium', 'Strong'][passwordRules.phase]
  const strengthColor = [
    '',
    'bg-red-500',
    'bg-amber-500',
    'bg-emerald-500',
  ][passwordRules.phase]
  const strengthTextColor = [
    '',
    'text-red-400',
    'text-amber-400',
    'text-emerald-400',
  ][passwordRules.phase]

  const passwordsMatch = confirmPassword.length > 0 && password === confirmPassword
  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword

  const canSubmit =
    fullName.trim().length > 0 &&
    email.trim().length > 0 &&
    passwordRules.phase === 3 &&
    passwordsMatch &&
    !loading

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)

    try {
      const username = fullName.trim().toLowerCase().replace(/\s+/g, '_')
      const res = await apiRegister(username, email, password)
      setTokens(res.tokens.access_token, res.tokens.refresh_token)
      router.push('/onboarding')
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 font-sans relative overflow-hidden transition-colors bg-[#0d1117]">
      <div className="absolute -top-10 -left-10 h-64 w-64 rounded-full blur-[100px] animate-pulse bg-rose-900/10"></div>
      <div className="absolute -bottom-10 -right-10 h-80 w-80 rounded-full blur-[100px] animate-pulse delay-1000 bg-rose-800/10"></div>

      <PageTransition
         className="w-full max-w-md border rounded-[2.5rem] p-10 relative overflow-hidden z-10 transition-all bg-[#161b22] border-rose-900/30 shadow-none"
      >

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl mb-4 text-white shadow-lg bg-rose-600 shadow-rose-900/20">
            <UserPlus className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">New Enrollment</h1>
          <p className="text-sm mt-2 font-medium text-slate-400">Create your Schale Account ID</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          {error && (
            <div className="rounded-xl px-4 py-3 text-sm font-medium bg-rose-900/30 text-rose-300">
              {error}
            </div>
          )}
          <div>
            <label className="text-[10px] font-black uppercase tracking-[0.2em] ml-2 text-rose-500">Full Name</label>
            <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Sensei Name"
                className="w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500"
            />
          </div>
          <div>
            <label className="text-[10px] font-black uppercase tracking-[0.2em] ml-2 text-rose-500">Email Address</label>
            <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="sensei@schale.edu"
                className="w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500"
            />
          </div>
          <div>
            <label className="text-[10px] font-black uppercase tracking-[0.2em] ml-2 text-rose-500">Secure Password</label>
            <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500"
            />

            <div className="flex mt-2 px-1 space-x-1">
              <div className={cn("h-1 flex-1 rounded-full transition-colors duration-300", passwordRules.phase >= 1 ? strengthColor : 'bg-rose-900/20')} />
              <div className={cn("h-1 flex-1 rounded-full transition-colors duration-300", passwordRules.phase >= 2 ? strengthColor : 'bg-rose-900/20')} />
              <div className={cn("h-1 flex-1 rounded-full transition-colors duration-300", passwordRules.phase >= 3 ? strengthColor : 'bg-rose-900/20')} />
            </div>

            {password.length > 0 && (
              <p className={cn('text-[10px] font-bold uppercase tracking-widest mt-1.5 ml-1', strengthTextColor)}>
                {strengthLabel}
              </p>
            )}

            {password.length > 0 && (
              <ul className="mt-2 ml-1 space-y-0.5">
                {passwordRules.rules.map((rule) => (
                  <li key={rule.label} className="flex items-center gap-1.5">
                    {rule.met
                      ? <Check className="h-3 w-3 text-emerald-500" />
                      : <X className="h-3 w-3 text-slate-600" />
                    }
                    <span className={cn('text-[10px]', rule.met ? 'text-emerald-500 font-semibold' : 'text-slate-500')}>
                      {rule.label}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <label className="text-[10px] font-black uppercase tracking-[0.2em] ml-2 text-rose-500">Re-typed Password</label>
            <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className={cn(
                    "w-full px-5 py-4 border rounded-2xl transition-all outline-none focus:ring-4 bg-[#0d1117] border-rose-900/30 text-white placeholder:text-slate-600 focus:ring-rose-900/20 focus:border-rose-500",
                    passwordsMatch && 'ring-4 ring-emerald-900/30 border-emerald-500',
                    passwordsMismatch && 'ring-4 ring-red-900/30 border-red-500',
                )}
            />
            {passwordsMatch && (
              <p className="flex items-center gap-1 mt-1.5 ml-1 text-[10px] font-bold text-emerald-500 uppercase tracking-widest">
                <Check className="h-3 w-3" /> Passwords match
              </p>
            )}
            {passwordsMismatch && (
              <p className="flex items-center gap-1 mt-1.5 ml-1 text-[10px] font-bold text-red-500 uppercase tracking-widest">
                <X className="h-3 w-3" /> Passwords do not match
              </p>
            )}
          </div>

            <button
                disabled={!canSubmit}
                className="w-full py-4 text-white font-black rounded-2xl shadow-xl mt-8 transition-all active:scale-95 uppercase tracking-widest text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center bg-rose-600 hover:bg-rose-500 shadow-rose-900/20"
            >
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Initiate Enrollment'}
            </button>
        </form>

        <p className="text-center mt-8 text-xs font-bold uppercase tracking-tight text-slate-500">
          Already have an ID? <Link href="/login" className="hover:underline text-rose-500">Log In</Link>
        </p>
      </PageTransition>
    </div>
  )
}
