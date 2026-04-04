"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart, Eye, Settings, TrendingUp, MessageCircle, Sparkles } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { cn } from '@/shared/lib/utils'
import { useInterventionStore } from '@/features/rio/store'
import { useEmotionalStore } from '@/features/emotional/store'

const RELATIONSHIP_TIERS = {
  stranger: { label: 'Stranger', color: 'text-slate-400', threshold: 0 },
  acquaintance: { label: 'Acquaintance', color: 'text-blue-400', threshold: 200 },
  friend: { label: 'Friend', color: 'text-emerald-400', threshold: 400 },
  close_friend: { label: 'Close Friend', color: 'text-purple-400', threshold: 600 },
  bonded: { label: 'Bonded', color: 'text-rose-400', threshold: 800 },
}

export interface ActivityData {
  sessionDuration: number
  idleTime: number
  eventCount: number
  lastActivityTime: number
  isLateNight: boolean
  isWeekend: boolean
}

export interface RioSidebarContentProps {
  activityData: ActivityData
  onCollapse: () => void
}

function formatTime(ms: number): string {
  const minutes = Math.floor(ms / (60 * 1000))
  const hours = Math.floor(minutes / 60)
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  return `${minutes}m`
}

export function RioSidebarContent({ activityData, onCollapse }: RioSidebarContentProps) {
  const router = useRouter()
  const [showSettings, setShowSettings] = useState(false)

  const { preferences, updatePreferences } = useInterventionStore()
  const { mood, affinity, relationshipTier, streakDays, recordHeadpat } = useEmotionalStore()

  const currentTier = RELATIONSHIP_TIERS[relationshipTier] || RELATIONSHIP_TIERS.stranger
  const nextTier = Object.values(RELATIONSHIP_TIERS).find((t) => t.threshold > affinity)

  const handleHeadpat = async () => {
    const result = await recordHeadpat('rio')
    if (result) {
      console.log('Headpat!', result)
    }
  }

  return (
    <>
      {/* Relationship Status */}
      <div>
        <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-3">
          Relationship Status
        </h3>
        <div className="p-4 rounded-xl bg-gradient-to-br from-rose-500/10 to-purple-500/10 border border-rose-500/30">
          <div className="flex items-center justify-between mb-3">
            <span className={cn('text-sm font-black', currentTier.color)}>{currentTier.label}</span>
            <span className="text-xs font-bold text-white/50">
              {affinity} / {nextTier?.threshold || 1000}
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-black/40 overflow-hidden mb-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(affinity / (nextTier?.threshold || 1000)) * 100}%` }}
              className="h-full bg-gradient-to-r from-rose-500 to-purple-500 rounded-full"
            />
          </div>
          {nextTier && (
            <p className="text-[10px] text-white/50 font-medium">
              {nextTier.threshold - affinity} affinity until {nextTier.label}
            </p>
          )}
        </div>

        {/* Headpat button */}
        <button
          onClick={handleHeadpat}
          className="w-full mt-3 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-sm font-bold text-white transition-colors flex items-center justify-center gap-2"
        >
          <Heart size={16} />
          Give Headpat (+5 affinity)
        </button>
      </div>

      {/* Session Stats */}
      <div>
        <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-3">
          Current Session
        </h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
            <span className="text-xs font-medium text-white/70">Session Duration</span>
            <span className="text-sm font-black text-white">{formatTime(activityData.sessionDuration)}</span>
          </div>
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
            <span className="text-xs font-medium text-white/70">Idle Time</span>
            <span className="text-sm font-black text-white">{formatTime(activityData.idleTime)}</span>
          </div>
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
            <span className="text-xs font-medium text-white/70">Activity Events</span>
            <span className="text-sm font-black text-white">{activityData.eventCount.toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
            <span className="text-xs font-medium text-white/70">Streak</span>
            <span className="text-sm font-black text-emerald-400">{streakDays} days 🔥</span>
          </div>
        </div>
      </div>

      {/* Rio's Observations */}
      <div>
        <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-3">
          What I've Noticed
        </h3>
        <div className="space-y-3">
          {activityData.sessionDuration > 45 * 60 * 1000 && (
            <div className="flex items-start gap-3 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <Sparkles size={16} className="text-amber-400 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-white">
                  You've been focused for over 45 minutes. Great dedication!
                </p>
              </div>
            </div>
          )}
          {activityData.isLateNight && (
            <div className="flex items-start gap-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30">
              <Eye size={16} className="text-red-400 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-white">It's very late. Please consider getting some rest.</p>
              </div>
            </div>
          )}
          {activityData.isWeekend && activityData.sessionDuration > 30 * 60 * 1000 && (
            <div className="flex items-start gap-3 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <TrendingUp size={16} className="text-blue-400 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-white">Working on the weekend? Don't forget to take breaks!</p>
              </div>
            </div>
          )}
          {!activityData.isLateNight &&
            !activityData.isWeekend &&
            activityData.sessionDuration < 30 * 60 * 1000 && (
              <div className="flex items-start gap-3 px-3 py-2 rounded-lg bg-white/5">
                <Eye size={16} className="text-white/50 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-white/70">All quiet so far. I'm here if you need anything.</p>
                </div>
              </div>
            )}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <button
            onClick={() => {
              router.push('/operation')
              onCollapse()
            }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-sm font-bold text-white transition-colors"
          >
            <MessageCircle size={16} />
            Talk to Rio
          </button>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-sm font-bold text-white transition-colors"
          >
            <Settings size={16} />
            Intervention Settings
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-4">
              <h4 className="text-sm font-black text-white mb-3">Intervention Preferences</h4>

              {/* Aggressiveness */}
              <div>
                <label className="text-xs font-bold text-white/70 mb-2 block">Intervention Style</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['gentle', 'balanced', 'aggressive'] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => updatePreferences({ aggressiveness: level })}
                      className={cn(
                        'px-3 py-2 rounded-lg text-xs font-bold transition-all',
                        preferences.aggressiveness === level
                          ? 'bg-rose-500 text-white'
                          : 'bg-white/10 text-white/50 hover:bg-white/20'
                      )}
                    >
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Break frequency */}
              <div>
                <label className="text-xs font-bold text-white/70 mb-2 block">Break Reminders</label>
                <div className="grid grid-cols-3 gap-2">
                  {([45, 60, 90, 0] as const).map((freq) => (
                    <button
                      key={freq}
                      onClick={() => updatePreferences({ breakFrequency: freq })}
                      className={cn(
                        'px-3 py-2 rounded-lg text-xs font-bold transition-all',
                        preferences.breakFrequency === freq
                          ? 'bg-rose-500 text-white'
                          : 'bg-white/10 text-white/50 hover:bg-white/20'
                      )}
                    >
                      {freq === 0 ? 'Off' : `${freq}m`}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-2">
                <label className="flex items-center justify-between">
                  <span className="text-xs font-medium text-white/70">Work Hour Limits</span>
                  <input
                    type="checkbox"
                    checked={preferences.workHourLimits}
                    onChange={(e) => updatePreferences({ workHourLimits: e.target.checked })}
                    className="rounded bg-white/10 border-white/20"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-xs font-medium text-white/70">Allow Blocking</span>
                  <input
                    type="checkbox"
                    checked={preferences.allowBlocking}
                    onChange={(e) => updatePreferences({ allowBlocking: e.target.checked })}
                    className="rounded bg-white/10 border-white/20"
                  />
                </label>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status footer */}
      <div className="pt-4 border-t border-white/10">
        <div className="flex items-center gap-2 text-xs text-white/50">
          <Eye size={14} />
          <span className="font-medium">Rio is watching over you</span>
        </div>
        <p className="text-[10px] text-white/30 mt-1">
          Last check: {formatTime(Date.now() - activityData.lastActivityTime)} ago
        </p>
      </div>
    </>
  )
}
