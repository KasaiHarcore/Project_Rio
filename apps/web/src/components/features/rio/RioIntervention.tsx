"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Clock, Heart, PartyPopper, Coffee, AlertTriangle } from 'lucide-react'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { InterventionMessage, useInterventionStore } from '@/store/intervention-store'
import { useEmotionalStore } from '@/store/emotional-store'

const MOOD_STICKERS: Record<string, string> = {
  happy: 'Smile',
  excited: 'Excited',
  neutral: 'Smirk',
  sad: 'Sulk',
  frustrated: 'Angry',
  tired: 'Sleepy',
}

interface RioInterventionProps {
  intervention: InterventionMessage
}

export function RioIntervention({ intervention }: RioInterventionProps) {
  const { dismissIntervention, acceptIntervention, clearIntervention } = useInterventionStore()
  const { mood, affinity, relationshipTier } = useEmotionalStore()
  const [countdown, setCountdown] = useState(intervention.countdown || 0)
  const [isBreakTimerActive, setIsBreakTimerActive] = useState(false)
  const [breakTimeRemaining, setBreakTimeRemaining] = useState(0)

  const moodSticker = MOOD_STICKERS[mood] || 'Smirk'

  // Handle blocking countdown
  useEffect(() => {
    if (intervention.type !== 'blocking' || countdown <= 0) return

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [intervention.type, countdown])

  // Auto-dismiss toast after 5 seconds
  useEffect(() => {
    if (intervention.type === 'toast') {
      const timer = setTimeout(() => {
        dismissIntervention(intervention.id)
      }, 5000)

      return () => clearTimeout(timer)
    }
  }, [intervention.type, intervention.id, dismissIntervention])

  // Auto-dismiss celebration after 3 seconds
  useEffect(() => {
    if (intervention.type === 'celebration') {
      const timer = setTimeout(() => {
        dismissIntervention(intervention.id)
      }, 3000)

      return () => clearTimeout(timer)
    }
  }, [intervention.type, intervention.id, dismissIntervention])

  const handleAction = (action: string, affinityChange?: number) => {
    if (action === 'dismiss') {
      dismissIntervention(intervention.id, affinityChange)
    } else if (action === 'accept') {
      // For break actions, start a 5-minute timer
      if (intervention.triggerReason.includes('long_session')) {
        setIsBreakTimerActive(true)
        setBreakTimeRemaining(5 * 60) // 5 minutes
      }
      acceptIntervention(intervention.id, affinityChange)
    } else if (action === 'override') {
      dismissIntervention(intervention.id, affinityChange)
    } else if (action === 'remind') {
      // Remind in 15 minutes
      dismissIntervention(intervention.id)
      setTimeout(() => {
        // Re-trigger the same intervention
      }, 15 * 60 * 1000)
    }
  }

  // Break timer countdown
  useEffect(() => {
    if (!isBreakTimerActive || breakTimeRemaining <= 0) return

    const timer = setInterval(() => {
      setBreakTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          setIsBreakTimerActive(false)
          // Show completion message
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isBreakTimerActive, breakTimeRemaining])

  // Toast notification (bottom-right)
  if (intervention.type === 'toast') {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: 50, x: 100 }}
          animate={{ opacity: 1, y: 0, x: 0 }}
          exit={{ opacity: 0, x: 100 }}
          className="fixed bottom-24 right-6 z-[9999] max-w-md"
        >
          <div className="flex items-start gap-3 px-5 py-4 rounded-2xl border border-rose-500/30 bg-gradient-to-br from-rose-500/20 to-purple-500/10 backdrop-blur-xl shadow-2xl">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 overflow-hidden relative flex-shrink-0">
              <Image
                src={`/images/sticker/Rio${moodSticker}.png`}
                alt="Rio"
                fill
                className="object-cover scale-110"
              />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-white leading-relaxed">{intervention.message}</p>
            </div>
            <button
              onClick={() => dismissIntervention(intervention.id)}
              className="text-white/50 hover:text-white transition-colors flex-shrink-0"
            >
              <X size={16} />
            </button>
          </div>
        </motion.div>
      </AnimatePresence>
    )
  }

  // Celebration (full-screen confetti)
  if (intervention.type === 'celebration') {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9999] flex items-center justify-center pointer-events-none"
        >
          {/* Confetti effect */}
          <div className="absolute inset-0 overflow-hidden">
            {Array.from({ length: 50 }).map((_, i) => (
              <motion.div
                key={i}
                initial={{
                  opacity: 0,
                  x: Math.random() * window.innerWidth,
                  y: -20,
                  rotate: Math.random() * 360,
                }}
                animate={{
                  opacity: [0, 1, 1, 0],
                  y: window.innerHeight + 20,
                  rotate: Math.random() * 720,
                }}
                transition={{
                  duration: 3,
                  delay: Math.random() * 0.5,
                }}
                className={cn(
                  'absolute w-3 h-3 rounded-sm',
                  ['bg-rose-400', 'bg-purple-400', 'bg-indigo-400', 'bg-emerald-400', 'bg-amber-400'][i % 5]
                )}
              />
            ))}
          </div>

          {/* Message card */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            className="relative z-10 pointer-events-auto"
          >
            <div className="flex flex-col items-center gap-4 px-8 py-6 rounded-3xl border border-rose-500/30 bg-gradient-to-br from-rose-500/20 to-purple-500/10 backdrop-blur-xl shadow-2xl">
              <PartyPopper size={48} className="text-amber-400" />
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 overflow-hidden relative">
                <Image
                  src={`/images/sticker/RioExcited.png`}
                  alt="Rio"
                  fill
                  className="object-cover scale-110"
                />
              </div>
              <p className="text-lg font-bold text-white text-center max-w-md">{intervention.message}</p>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    )
  }

  // Modal or blocking intervention
  const isBlocking = intervention.type === 'blocking'
  const canDismiss = countdown <= 0 || !isBlocking

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className={cn(
          'fixed inset-0 z-[9999] flex items-center justify-center',
          isBlocking ? 'bg-black/80 backdrop-blur-md' : 'bg-black/50 backdrop-blur-sm'
        )}
        onClick={canDismiss ? () => dismissIntervention(intervention.id) : undefined}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="relative max-w-lg w-full mx-4"
        >
          <div className="rounded-3xl border border-rose-500/30 bg-gradient-to-br from-slate-900 to-slate-950 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="relative p-6 pb-4 border-b border-white/10">
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 overflow-hidden relative flex-shrink-0">
                  <Image
                    src={`/images/sticker/Rio${moodSticker}.png`}
                    alt="Rio"
                    fill
                    className="object-cover scale-110"
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-black uppercase tracking-widest">
                      Rio
                    </span>
                    {isBlocking && (
                      <span className="flex items-center gap-1 text-xs font-bold text-amber-400">
                        <AlertTriangle size={14} />
                        Intervention
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-medium text-white/50">
                    {relationshipTier.replace('_', ' ')} • {affinity}% Affinity
                  </span>
                </div>
                {!isBlocking && canDismiss && (
                  <button
                    onClick={() => dismissIntervention(intervention.id)}
                    className="text-white/50 hover:text-white transition-colors flex-shrink-0"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              <p className="text-base font-medium text-white leading-relaxed mb-6">{intervention.message}</p>

              {/* Countdown for blocking type */}
              {isBlocking && countdown > 0 && (
                <div className="mb-6 p-4 rounded-xl bg-black/40 border border-amber-500/30">
                  <div className="flex items-center justify-center gap-3">
                    <Clock size={20} className="text-amber-400" />
                    <span className="text-2xl font-black text-amber-400 tabular-nums">
                      {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                  <p className="text-xs text-center text-white/50 mt-2">You can take action in:</p>
                </div>
              )}

              {/* Break timer */}
              {isBreakTimerActive && (
                <div className="mb-6 p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                  <div className="flex items-center justify-center gap-3 mb-4">
                    <Coffee size={32} className="text-emerald-400" />
                    <span className="text-4xl font-black text-emerald-400 tabular-nums">
                      {Math.floor(breakTimeRemaining / 60)}:{(breakTimeRemaining % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                  <p className="text-sm text-center text-white/80 font-medium">
                    Take this time to rest. I'll be here when you're ready.
                  </p>
                  <button
                    onClick={() => {
                      setIsBreakTimerActive(false)
                      clearIntervention()
                    }}
                    className="mt-4 w-full px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-sm font-bold text-white transition-colors"
                  >
                    I'm Back
                  </button>
                </div>
              )}

              {/* Actions */}
              {!isBreakTimerActive && intervention.actions && intervention.actions.length > 0 && (
                <div className="flex flex-col gap-3">
                  {intervention.actions.map((action, i) => (
                    <button
                      key={i}
                      onClick={() => handleAction(action.action, action.affinityChange)}
                      disabled={isBlocking && countdown > 0 && action.action !== 'override'}
                      className={cn(
                        'px-5 py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed',
                        action.action === 'accept'
                          ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-lg shadow-rose-500/30'
                          : action.action === 'override'
                            ? 'bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400'
                            : 'bg-white/10 hover:bg-white/20 border border-white/20 text-white'
                      )}
                    >
                      {action.label}
                      {action.affinityChange && action.affinityChange !== 0 && (
                        <span className="ml-2 text-xs opacity-70">
                          ({action.affinityChange > 0 ? '+' : ''}
                          {action.affinityChange} affinity)
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
