"use client"

import React, { useState, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Save } from 'lucide-react'
import {
  apiUpdateProfile,
  UserProfileData,
} from '@/features/settings/api'
import { ApiError } from '@/shared/api/client'
import { SettingsInput, SettingsTextarea, SectionHeader, SaveMessage } from './primitives'

// ─── Types ──────────────────────────────────────────────────────────

interface ProfileTabProps {
  profile: UserProfileData | null
  onReload: () => void
}

// ─── Component ──────────────────────────────────────────────────────

export function ProfileTab({ profile, onReload }: ProfileTabProps) {
  const [name, setName] = useState(profile?.full_name || '')
  const [bio, setBio] = useState(profile?.bio || '')
  const [studyGoal, setStudyGoal] = useState(profile?.study_goal || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (profile) {
      setName(profile.full_name || '')
      setBio(profile.bio || '')
      setStudyGoal(profile.study_goal || '')
    }
  }, [profile])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await apiUpdateProfile({
        full_name: name || undefined,
        bio: bio || undefined,
        study_goal: studyGoal || undefined,
      })
      setMessage({ type: 'success', text: 'Profile saved successfully!' })
      setTimeout(() => setMessage(null), 3000)
      onReload()
    } catch (err) {
      const error = err as ApiError
      setMessage({ type: 'error', text: error.message || 'Failed to save profile' })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <section>
        <SectionHeader title="Personal Information" />
        <div className="space-y-4">
          <SettingsInput label="Display Name" placeholder="Your name" value={name} onChange={setName} />
          <SettingsTextarea label="Bio / About" placeholder="Tell us about yourself..." value={bio} onChange={setBio} rows={3} hint="Optional" />
          <SettingsTextarea label="Study Goals" placeholder="e.g., Master Python by Q3, Pass AWS certification, Build a full-stack app..." value={studyGoal} onChange={setStudyGoal} rows={3} hint="Helps the AI tailor guidance" />
        </div>
      </section>

      <div className="pt-2 flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40"
        >
          <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Profile'}
        </button>
        <AnimatePresence>
          {message && <SaveMessage type={message.type} message={message.text} />}
        </AnimatePresence>
      </div>
    </div>
  )
}
