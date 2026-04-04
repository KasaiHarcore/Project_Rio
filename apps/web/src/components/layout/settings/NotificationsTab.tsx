"use client"

import React, { useState, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Save } from 'lucide-react'
import { UserSettings } from '@/features/settings/api'
import { ApiError } from '@/shared/api/client'
import { ToggleRow, SectionHeader, SaveMessage } from './primitives'

// ─── Types ──────────────────────────────────────────────────────────

interface NotificationsTabProps {
  settings: UserSettings | null
  onReload: () => void
}

// ─── Component ──────────────────────────────────────────────────────

export function NotificationsTab({ settings, onReload }: NotificationsTabProps) {
  const [missionReminders, setMissionReminders] = useState(settings?.mission_reminders ?? true)
  const [chatAlerts, setChatAlerts] = useState(settings?.chat_alerts ?? true)
  const [systemUpdates, setSystemUpdates] = useState(settings?.system_updates ?? false)
  const [weeklySummary, setWeeklySummary] = useState(settings?.weekly_summary ?? true)
  const [errorAlerts, setErrorAlerts] = useState(settings?.error_alerts ?? true)
  const [soundEnabled, setSoundEnabled] = useState(settings?.sound_enabled ?? false)
  const [emailNotifs, setEmailNotifs] = useState(settings?.email_notifications ?? false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (settings) {
      setMissionReminders(settings.mission_reminders)
      setChatAlerts(settings.chat_alerts)
      setSystemUpdates(settings.system_updates)
      setWeeklySummary(settings.weekly_summary)
      setErrorAlerts(settings.error_alerts)
      setSoundEnabled(settings.sound_enabled)
      setEmailNotifs(settings.email_notifications)
    }
  }, [settings])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const { apiUpdateSettings } = await import('@/features/settings/api')
      await apiUpdateSettings({
        mission_reminders: missionReminders,
        chat_alerts: chatAlerts,
        system_updates: systemUpdates,
        weekly_summary: weeklySummary,
        error_alerts: errorAlerts,
        sound_enabled: soundEnabled,
        email_notifications: emailNotifs,
      })
      setMessage({ type: 'success', text: 'Notification preferences saved!' })
      setTimeout(() => setMessage(null), 3000)
      onReload()
    } catch (err) {
      const error = err as ApiError
      setMessage({ type: 'error', text: error.message || 'Failed to save preferences' })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <section>
        <SectionHeader title="Notification Preferences" />
        <div className="space-y-3">
          <ToggleRow label="Mission Reminders" description="Get notified when a mission deadline is approaching" enabled={missionReminders} onChange={setMissionReminders} />
          <ToggleRow label="Chat Response Alerts" description="Notify when AI finishes a long-running response" enabled={chatAlerts} onChange={setChatAlerts} />
          <ToggleRow label="System Updates" description="Announcements about new features and maintenance" enabled={systemUpdates} onChange={setSystemUpdates} />
          <ToggleRow label="Weekly Progress Summary" description="Receive a weekly study progress report" enabled={weeklySummary} onChange={setWeeklySummary} />
          <ToggleRow label="Error Notifications" description="Alert when system encounters errors or connection issues" enabled={errorAlerts} onChange={setErrorAlerts} />
        </div>
      </section>
      <section>
        <SectionHeader title="Delivery" />
        <div className="space-y-3">
          <ToggleRow label="Sound Effects" description="Play sound when notifications arrive" enabled={soundEnabled} onChange={setSoundEnabled} />
          <ToggleRow label="Email Notifications" description="Send important alerts to your email address" enabled={emailNotifs} onChange={setEmailNotifs} />
        </div>
      </section>
      <div className="pt-2 flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40"
        >
          <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Preferences'}
        </button>
        <AnimatePresence>
          {message && <SaveMessage type={message.type} message={message.text} />}
        </AnimatePresence>
      </div>
    </div>
  )
}
