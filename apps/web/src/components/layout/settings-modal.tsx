"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User, Bell, Database, Shield, Trash2,
  Eye, EyeOff, Download, Archive,
  AlertTriangle, LogOut, Save, Lock, FileText, Settings
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useUIStore } from '@/shared/store/ui-store'
import {
  apiGetSettings,
  apiUpdateProfile,
  UserProfileData,
} from '@/features/settings/api'
import { apiResetPassword } from '@/features/auth/api'
import { ApiError } from '@/shared/api/client'
import { ApiModelTab } from '@/features/settings/components/ApiModelTab'

// ─── Types ──────────────────────────────────────────────────────────
interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type TabId = 'profile' | 'notifications' | 'data' | 'security' | 'api-model'

interface ToggleSetting {
  id: string; label: string; description: string; enabled: boolean
}

// ─── Reusable Primitives ────────────────────────────────────────────

function SettingsInput({ label, type = 'text', placeholder, value, onChange, rightElement, className }: {
  label: string; type?: string; placeholder?: string; value: string; onChange: (v: string) => void; rightElement?: React.ReactNode; className?: string
}) {
  return (
    <div className={cn("rounded-2xl border p-4 transition-colors bg-[var(--settings-input-bg)] border-[var(--settings-input-border)] focus-within:border-[var(--settings-input-focus-border)] focus-within:bg-[var(--settings-input-focus-bg)]", className)}>
      <label className="text-[9px] font-black tracking-widest uppercase block mb-1.5 text-[var(--settings-input-label)]">{label}</label>
      <div className="flex items-center gap-2">
        <input type={type} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full bg-transparent font-mono text-sm font-bold outline-none text-[var(--settings-input-text)] placeholder:text-slate-400/50" />
        {rightElement}
      </div>
    </div>
  )
}

function SettingsTextarea({ label, placeholder, value, onChange, rows = 6, hint }: {
  label: string; placeholder?: string; value: string; onChange: (v: string) => void; rows?: number; hint?: string
}) {
  return (
    <div className="rounded-2xl border p-4 transition-colors bg-[var(--settings-input-bg)] border-[var(--settings-input-border)] focus-within:border-[var(--settings-input-focus-border)] focus-within:bg-[var(--settings-input-focus-bg)]">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-[9px] font-black tracking-widest uppercase text-[var(--settings-input-label)]">{label}</label>
        {hint && <span className="text-[9px] font-bold text-slate-400">{hint}</span>}
      </div>
      <textarea placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} rows={rows}
        className="w-full bg-transparent text-sm font-medium outline-none resize-none text-[var(--settings-input-text)] placeholder:text-slate-400/50 leading-relaxed" />
    </div>
  )
}

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!enabled)}
      className={cn("h-6 w-11 rounded-full relative cursor-pointer transition-colors flex-shrink-0",
        enabled ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
      )}>
      <div className={cn("absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
        enabled ? "translate-x-[22px]" : "translate-x-1"
      )} />
    </button>
  )
}

function ToggleRow({ label, description, enabled, onChange }: {
  label: string; description: string; enabled: boolean; onChange: (v: boolean) => void
}) {
  return (
    <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="pr-4">
        <p className="text-sm font-bold text-[var(--settings-section-title)]">{label}</p>
        <p className="text-xs text-slate-400 mt-1">{description}</p>
      </div>
      <Toggle enabled={enabled} onChange={onChange} />
    </div>
  )
}

function DangerButton({ icon: Icon, label, description, onClick, confirmLabel }: {
  icon: React.ComponentType<Record<string, unknown>>; label: string; description: string; onClick: () => void; confirmLabel?: string
}) {
  const [confirming, setConfirming] = useState(false)
  const handleClick = () => {
    if (confirmLabel && !confirming) { setConfirming(true); setTimeout(() => setConfirming(false), 3000); return }
    onClick(); setConfirming(false)
  }
  return (
    <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0">
          <Icon className="h-5 w-5 text-red-500" />
        </div>
        <div>
          <p className="text-sm font-bold text-[var(--settings-section-title)]">{label}</p>
          <p className="text-xs text-slate-400 mt-0.5">{description}</p>
        </div>
      </div>
      <button onClick={handleClick}
        className={cn("px-4 py-2 rounded-xl text-xs font-bold transition-all border",
          confirming ? "bg-red-500 text-white border-red-500 animate-pulse" : "bg-transparent text-red-500 border-red-200 hover:bg-red-500 hover:text-white hover:border-red-500"
        )}>
        {confirming ? (confirmLabel || 'Confirm?') : label}
      </button>
    </div>
  )
}

function SectionHeader({ title, badge }: { title: string; badge?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
      <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">{title}</h3>
      {badge}
    </div>
  )
}

function SaveMessage({ type, message }: { type: 'success' | 'error'; message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        "text-xs font-bold px-4 py-2 rounded-xl",
        type === 'success' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
      )}
    >
      {message}
    </motion.div>
  )
}

// ─── 1. Profile Tab ─────────────────────────────────────────────────

function ProfileTab({ profile, onReload }: { profile: UserProfileData | null; onReload: () => void }) {
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

// ─── 2. Notifications Tab ───────────────────────────────────────────

function NotificationsTab({ settings, onReload }: { settings: any | null; onReload: () => void }) {
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

// ─── 3. Data Management Tab ─────────────────────────────────────────

function DataManagementTab() {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'md'>('json')

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Export */}
      <section>
        <SectionHeader title="Export Data" />
        <div className="rounded-2xl border p-6 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
          <p className="text-sm font-bold text-[var(--settings-section-title)] mb-1">Export Chat History</p>
          <p className="text-xs text-slate-400 mb-4">Download all your conversations in the format of your choice.</p>
          <div className="flex items-center gap-3">
            {(['json', 'csv', 'md'] as const).map((fmt) => (
              <button key={fmt} onClick={() => setExportFormat(fmt)}
                className={cn("px-4 py-2 rounded-xl text-xs font-bold uppercase border transition-all",
                  exportFormat === fmt
                    ? "bg-[var(--settings-tab-active-bg)] text-white border-transparent"
                    : "bg-transparent border-[var(--settings-card-border)] text-[var(--settings-section-title)] hover:border-[var(--settings-input-focus-border)]"
                )}>
                .{fmt}
              </button>
            ))}
            <button className="ml-auto flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-[var(--settings-tab-active-bg)] text-white transition-all hover:opacity-90 active:scale-[0.98]">
              <Download className="h-4 w-4" /> Export
            </button>
          </div>
        </div>
      </section>

      {/* Archive */}
      <section>
        <SectionHeader title="Archive" />
        <div className="rounded-2xl border p-6 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <Archive className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-[var(--settings-section-title)]">Archive All History</p>
              <p className="text-xs text-slate-400 mt-0.5">Move all conversations to archive. They can be restored later.</p>
            </div>
          </div>
          <button className="px-4 py-2 rounded-xl text-xs font-bold border transition-all text-amber-600 border-amber-200 hover:bg-amber-500 hover:text-white hover:border-amber-500">
            Archive
          </button>
        </div>
      </section>

      {/* Danger Zone */}
      <section>
        <SectionHeader title="Danger Zone" badge={<span className="text-[10px] font-bold text-red-400 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> IRREVERSIBLE</span>} />
        <div className="space-y-3">
          <DangerButton icon={Trash2} label="Delete History" description="Permanently delete all chat conversations" onClick={() => {}} confirmLabel="Click again to confirm" />
          <DangerButton icon={Database} label="Clear Knowledge Base" description="Remove all uploaded documents from the vector store" onClick={() => {}} confirmLabel="Click again to confirm" />
          <DangerButton icon={FileText} label="Clear Artifacts" description="Delete all generated artifacts and cached outputs" onClick={() => {}} confirmLabel="Click again to confirm" />
        </div>
      </section>
    </div>
  )
}

// ─── 4. Security Tab ────────────────────────────────────────────────

function SecurityTab() {
  const [currentPassword, setCurrentPassword] = useState('')
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
      setCurrentPassword('')
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

// ─── Tab Registry ───────────────────────────────────────────────────
const TABS: { id: TabId; label: string; icon: React.ComponentType<Record<string, unknown>> }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api-model', label: 'API & Model', icon: Settings },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'data', label: 'Data', icon: Database },
  { id: 'security', label: 'Security', icon: Shield },
]

// ─── Main Modal ─────────────────────────────────────────────────────
export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const [settings, setSettings] = useState<any | null>(null)
  const [profile, setProfile] = useState<UserProfileData | null>(null)
  const [loading, setLoading] = useState(true)

  // Fetch settings on mount
  useEffect(() => {
    if (isOpen) {
      loadSettings()
    }
  }, [isOpen])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const data = await apiGetSettings()
      setSettings(data.settings)
      setProfile(data.profile)
    } catch (err) {
      console.error('Failed to load settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--settings-tab-active-bg)] mx-auto mb-4" />
            <p className="text-sm text-slate-400 font-bold">Loading settings...</p>
          </div>
        </div>
      )
    }

    switch (activeTab) {
      case 'profile':
        return <ProfileTab profile={profile} onReload={loadSettings} />
      case 'api-model':
        return <ApiModelTab settings={settings} onReload={loadSettings} />
      case 'notifications':
        return <NotificationsTab settings={settings} onReload={loadSettings} />
      case 'data':
        return <DataManagementTab />
      case 'security':
        return <SecurityTab />
      default:
        return null
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 font-sans">
          {/* Backdrop */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-md" />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative flex flex-col md:flex-row h-[min(750px,90vh)] w-full max-w-5xl overflow-hidden rounded-[2.5rem] border shadow-2xl z-10 bg-[var(--settings-bg)] border-[var(--settings-border)]"
            style={{ boxShadow: `0 25px 50px -12px var(--settings-shadow)` }}
          >
            {/* Sidebar */}
            <aside className="w-full md:w-56 border-b md:border-b-0 md:border-r p-4 md:p-6 flex flex-col bg-[var(--settings-sidebar-bg)] border-[var(--settings-sidebar-border)]">
              <div className="mb-4 md:mb-8">
                <h2 className="text-[10px] font-black tracking-[0.2em] uppercase text-[var(--settings-heading)]">System Settings</h2>
              </div>
              <nav className="flex md:flex-col gap-1 md:gap-0 md:space-y-1 flex-1 overflow-x-auto md:overflow-x-visible pb-2 md:pb-0">
                {TABS.map((tab) => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    aria-label={tab.label}
                    className={cn("flex items-center rounded-xl p-2 md:p-3 text-xs md:text-sm font-bold transition-all whitespace-nowrap md:w-full",
                      activeTab === tab.id
                        ? 'bg-[var(--settings-tab-active-bg)] text-white shadow-lg'
                        : 'text-[var(--settings-tab-inactive-text)] hover:bg-[var(--settings-tab-hover-bg)] hover:text-[var(--settings-tab-hover-text)]'
                    )}
                    style={activeTab === tab.id ? { boxShadow: `0 10px 15px -3px var(--settings-tab-active-shadow)` } : undefined}>
                    <tab.icon className="mr-2 md:mr-3 h-4 w-4" strokeWidth={2.5} />
                    <span className="hidden md:inline">{tab.label}</span>
                  </button>
                ))}
              </nav>
              <button onClick={onClose} aria-label="Close settings" className="hidden md:block text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase transition-colors hover:text-red-400 text-left">
                Close Terminal
              </button>
            </aside>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar">
              {renderContent()}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
