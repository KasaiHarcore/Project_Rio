"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Heart, Battery, Eye, Settings, TrendingUp, MessageCircle, Sparkles } from 'lucide-react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { RioIntervention } from './RioIntervention'
import { useInterventionStore } from '@/store/intervention-store'
import { useEmotionalStore } from '@/store/emotional-store'
import { useInterventionEngine } from '@/hooks/use-intervention-engine'
import { useActivityMonitor } from '@/hooks/use-activity-monitor'

const MOOD_STICKERS: Record<string, string> = {
  happy: 'Smile',
  excited: 'Excited',
  neutral: 'Smirk',
  sad: 'Sulk',
  frustrated: 'Angry',
  tired: 'Sleepy',
}

const RELATIONSHIP_TIERS = {
  stranger: { label: 'Stranger', color: 'text-slate-400', threshold: 0 },
  acquaintance: { label: 'Acquaintance', color: 'text-blue-400', threshold: 200 },
  friend: { label: 'Friend', color: 'text-emerald-400', threshold: 400 },
  close_friend: { label: 'Close Friend', color: 'text-purple-400', threshold: 600 },
  bonded: { label: 'Bonded', color: 'text-rose-400', threshold: 800 },
}

export function RioGuardian() {
  const router = useRouter()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const { currentIntervention, preferences, updatePreferences } = useInterventionStore()
  const { mood, energy, affinity, relationshipTier, streakDays, recordHeadpat } = useEmotionalStore()
  const activityData = useActivityMonitor()

  // Initialize intervention engine
  useInterventionEngine()

  const moodSticker = MOOD_STICKERS[mood] || 'Smirk'
  const currentTier = RELATIONSHIP_TIERS[relationshipTier] || RELATIONSHIP_TIERS.stranger
  const nextTier = Object.values(RELATIONSHIP_TIERS).find((t) => t.threshold > affinity)

  const handleHeadpat = async () => {
    const result = await recordHeadpat('rio')
    if (result) {
      // Show affinity flash notification
      console.log('Headpat!', result)
    }
  }

  const formatTime = (ms: number) => {
    const minutes = Math.floor(ms / (60 * 1000))
    const hours = Math.floor(minutes / 60)
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`
    }
    return `${minutes}m`
  }

  return (
    <>
      {/* Intervention overlay */}
      {currentIntervention && <RioIntervention intervention={currentIntervention} />}

      {/* Floating bubble (minimized state) */}
      <AnimatePresence>
        {!isExpanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="fixed bottom-6 right-6 z-[9998]"
          >
            <button
              onClick={() => setIsExpanded(true)}
              className="relative group"
              title="Rio is watching over you"
            >
              {/* Pulse animation */}
              <div className="absolute inset-0 rounded-full bg-rose-500/30 animate-ping opacity-75" />

              {/* Bubble */}
              <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-rose-500/20 to-purple-500/20 border-2 border-rose-500/50 overflow-hidden shadow-lg shadow-rose-500/30 hover:shadow-rose-500/50 transition-shadow">
                <Image
                  src={`/images/sticker/Rio${moodSticker}.png`}
                  alt="Rio"
                  fill
                  className="object-cover scale-110"
                />
              </div>

              {/* Status indicator */}
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-400 border-2 border-slate-900 animate-pulse" />

              {/* Tooltip */}
              <div className="absolute bottom-full right-0 mb-2 px-3 py-1.5 rounded-lg bg-black/90 text-white text-xs font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                Rio is observing
                <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-black/90" />
              </div>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Expanded sidebar */}
      <AnimatePresence>
        {isExpanded && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsExpanded(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9997]"
            />

            {/* Sidebar */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 bottom-0 w-[400px] bg-gradient-to-br from-slate-900 to-slate-950 border-l border-rose-500/30 shadow-2xl z-[9998] overflow-y-auto custom-scrollbar"
            >
              {/* Header */}
              <div className="sticky top-0 z-10 bg-gradient-to-br from-slate-900 to-slate-950 border-b border-white/10 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 overflow-hidden relative">
                      <Image
                        src={`/images/sticker/Rio${moodSticker}.png`}
                        alt="Rio"
                        fill
                        className="object-cover scale-110"
                      />
                    </div>
                    <div>
                      <h2 className="text-lg font-black text-white">Rio</h2>
                      <p className="text-xs text-white/50 font-medium">Background Guardian</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsExpanded(false)}
                    className="text-white/50 hover:text-white transition-colors"
                  >
                    <X size={20} />
                  </button>
                </div>

                {/* Quick stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="px-3 py-2 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-2 mb-1">
                      <Heart size={14} className="text-rose-400" />
                      <span className="text-xs font-bold text-white/70">Mood</span>
                    </div>
                    <p className="text-sm font-black text-white capitalize">{mood}</p>
                  </div>
                  <div className="px-3 py-2 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-2 mb-1">
                      <Battery size={14} className="text-emerald-400" />
                      <span className="text-xs font-bold text-white/70">Energy</span>
                    </div>
                    <p className="text-sm font-black text-white">{Math.round(energy * 100)}%</p>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
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
                        setIsExpanded(false)
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
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
