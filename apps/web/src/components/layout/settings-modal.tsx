"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Bell, Database, Shield, Settings } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { apiGetSettings, UserProfileData, UserSettings } from '@/features/settings/api'
import { ApiModelTab } from '@/features/settings/components/ApiModelTab'
import { ProfileTab } from './settings/ProfileTab'
import { NotificationsTab } from './settings/NotificationsTab'
import { DataManagementTab } from './settings/DataManagementTab'
import { SecurityTab } from './settings/SecurityTab'

// ─── Types ──────────────────────────────────────────────────────────

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type TabId = 'profile' | 'notifications' | 'data' | 'security' | 'api-model'

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
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [profile, setProfile] = useState<UserProfileData | null>(null)
  const [loading, setLoading] = useState(true)

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
