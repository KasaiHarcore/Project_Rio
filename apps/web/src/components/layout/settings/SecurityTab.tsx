"use client"

import React, { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, AlertTriangle, LogOut, Lock, Trash2 } from 'lucide-react'
import { apiResetPassword } from '@/features/auth/api'
import { ApiError } from '@/shared/api/client'
import { SettingsInput, DangerButton, SectionHeader, SaveMessage } from './primitives'

// ─── Component ──────────────────────────────────────────────────────

export function SecurityTab() {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const togglePassword = (id: string) => setShowPasswords(prev => ({ ...prev, [id]: !prev[id] }))
  const passwordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handlePasswordChange = async () => {
    if (!newPassword || passwordMismatch) return
    setSaving(true)
    setMessage(null)
    try {
      await apiResetPassword(newPassword)
      setMessage({ type: 'success', text: 'Password updated successfully!' })
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setMessage(null), 3000)
    } catch (err) {
      const error = err as ApiError
      setMessage({ type: 'error', text: error.message || 'Failed to update password' })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Change Password */}
      <section>
        <SectionHeader title="Change Password" />
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SettingsInput label="New Password" type={showPasswords['new'] ? 'text' : 'password'} placeholder="Enter new password" value={newPassword} onChange={setNewPassword}
              rightElement={<button onClick={() => togglePassword('new')} className="text-slate-400 hover:text-slate-600 transition-colors p-1">{showPasswords['new'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
            <div>
              <SettingsInput label="Confirm New Password" type={showPasswords['confirm'] ? 'text' : 'password'} placeholder="Confirm new password" value={confirmPassword} onChange={setConfirmPassword}
                rightElement={<button onClick={() => togglePassword('confirm')} className="text-slate-400 hover:text-slate-600 transition-colors p-1">{showPasswords['confirm'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
              {passwordMismatch && <p className="text-[10px] font-bold text-red-500 mt-2 ml-1">Passwords do not match</p>}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handlePasswordChange}
              disabled={!newPassword || passwordMismatch || saving}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Lock className="h-4 w-4" /> {saving ? 'Updating...' : 'Update Password'}
            </button>
            <AnimatePresence>
              {message && <SaveMessage type={message.type} message={message.text} />}
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* Logout + Delete */}
      <section>
        <SectionHeader title="Account Actions" badge={<span className="text-[10px] font-bold text-red-400 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> CRITICAL</span>} />
        <div className="space-y-3">
          <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                <LogOut className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-[var(--settings-section-title)]">Log Out</p>
                <p className="text-xs text-slate-400 mt-0.5">Sign out of this session</p>
              </div>
            </div>
            <button
              className="px-4 py-2 rounded-xl text-xs font-bold border transition-all text-amber-600 border-amber-200 hover:bg-amber-500 hover:text-white hover:border-amber-500"
              onClick={async () => {
                const { apiLogout } = await import('@/features/auth/api')
                await apiLogout()
                window.location.href = '/login'
              }}
            >
              Log Out
            </button>
          </div>
          <DangerButton icon={Trash2} label="Delete Account" description="Permanently delete your account and all associated data. This cannot be undone." onClick={() => {}} confirmLabel="I understand, delete my account" />
        </div>
      </section>
    </div>
  )
}
