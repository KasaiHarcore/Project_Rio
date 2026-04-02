"use client"

import { useEffect, useState } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { setTokens } from '@/features/auth/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function OAuthCallbackPage() {
  const params = useParams<{ provider: string }>()
  const searchParams = useSearchParams()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const provider = params.provider

    if (!code) {
      setError('No authorization code received from provider.')
      return
    }

    const qs = new URLSearchParams({ code, ...(state ? { state } : {}) })

    fetch(`${API_BASE}/api/v1/auth/oauth/${provider}/callback?${qs}`)
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.text().catch(() => '')
          throw new Error(body || `OAuth callback failed: ${res.status}`)
        }
        return res.json()
      })
      .then((data) => {
        setTokens(data.tokens.access_token, data.tokens.refresh_token)
        router.push('/')
        router.refresh()
      })
      .catch((err) => {
        setError(err?.message || 'OAuth login failed. Please try again.')
      })
  }, [params.provider, searchParams, router])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0d1117] p-6">
        <div className="w-full max-w-md rounded-2xl border border-rose-900/30 bg-[#161b22] p-8 text-center">
          <h2 className="mb-4 text-lg font-bold text-rose-400">Login Failed</h2>
          <p className="mb-6 text-sm text-slate-400">{error}</p>
          <a href="/login" className="text-sm font-semibold text-rose-500 hover:underline">
            Back to login
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d1117]">
      <div className="text-center">
        <div className="mb-4 inline-flex h-12 w-12 animate-spin items-center justify-center rounded-full border-2 border-rose-500 border-t-transparent" />
        <p className="text-sm text-slate-400">Completing login...</p>
      </div>
    </div>
  )
}
