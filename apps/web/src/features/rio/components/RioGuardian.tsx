"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Heart, Battery } from 'lucide-react'
import Image from 'next/image'
import { RioIntervention } from './RioIntervention'
import { RioNowPlaying } from './RioNowPlaying'
import { RioSidebarContent } from './RioSidebarContent'
import { useInterventionStore } from '@/features/rio/store'
import { useEmotionalStore } from '@/features/emotional/store'
import { useInterventionEngine } from '@/features/rio/hooks/use-intervention-engine'
import { useActivityMonitor } from '@/shared/hooks/use-activity-monitor'
import { useMusicStore } from '@/features/music/store'

export function RioGuardian() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showQueue, setShowQueue] = useState(false)

  const { currentIntervention } = useInterventionStore()
  const { mood, energy } = useEmotionalStore()
  const activityData = useActivityMonitor()

  // Music state
  const musicTracks = useMusicStore(s => s.tracks)
  const currentTrack = useMusicStore(s => s.currentTrack)
  const isPlaying = useMusicStore(s => s.isPlaying)
  const progress = useMusicStore(s => s.progress)
  const duration = useMusicStore(s => s.duration)
  const currentTime = useMusicStore(s => s.currentTime)
  const volume = useMusicStore(s => s.volume)
  const isMuted = useMusicStore(s => s.isMuted)
  const favoriteIds = useMusicStore(s => s.favoriteIds)
  const togglePlayPause = useMusicStore(s => s.togglePlayPause)
  const nextTrackAction = useMusicStore(s => s.nextTrack)
  const previousTrackAction = useMusicStore(s => s.previousTrack)
  const setVolume = useMusicStore(s => s.setVolume)
  const toggleMute = useMusicStore(s => s.toggleMute)
  const playTrack = useMusicStore(s => s.play)
  const seekTo = useMusicStore(s => s.seekTo)
  const toggleFavorite = useMusicStore(s => s.toggleFavorite)
  const isShuffled = useMusicStore(s => s.isShuffled)
  const repeatMode = useMusicStore(s => s.repeatMode)
  const toggleShuffle = useMusicStore(s => s.toggleShuffle)
  const setRepeatMode = useMusicStore(s => s.setRepeatMode)

  useInterventionEngine()

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
                  src="/images/avatar.png"
                  alt="Rio"
                  fill
                  className="object-contain"
                />
              </div>

              {/* Status indicator */}
              {isPlaying && currentTrack ? (
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-indigo-500 border-2 border-slate-900 flex items-end justify-center gap-[1.5px] pb-[3px]">
                  <span className="w-[2px] bg-white rounded-full animate-[bounce_0.5s_ease-in-out_infinite]" style={{ height: '40%' }} />
                  <span className="w-[2px] bg-white rounded-full animate-[bounce_0.5s_ease-in-out_infinite_0.15s]" style={{ height: '70%' }} />
                  <span className="w-[2px] bg-white rounded-full animate-[bounce_0.5s_ease-in-out_infinite_0.3s]" style={{ height: '40%' }} />
                </div>
              ) : (
                <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-400 border-2 border-slate-900 animate-pulse" />
              )}

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
                        src="/images/avatar.png"
                        alt="Rio"
                        fill
                        className="object-contain"
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
                {/* Now Playing */}
                <RioNowPlaying
                  currentTrack={currentTrack}
                  tracks={musicTracks}
                  isPlaying={isPlaying}
                  progress={progress}
                  duration={duration}
                  currentTime={currentTime}
                  volume={volume}
                  isMuted={isMuted}
                  isShuffled={isShuffled}
                  repeatMode={repeatMode}
                  favoriteIds={favoriteIds}
                  showQueue={showQueue}
                  onTogglePlayPause={togglePlayPause}
                  onNext={nextTrackAction}
                  onPrevious={previousTrackAction}
                  onSetVolume={setVolume}
                  onToggleMute={toggleMute}
                  onToggleShuffle={toggleShuffle}
                  onSetRepeatMode={setRepeatMode}
                  onPlay={playTrack}
                  onSeek={seekTo}
                  onToggleFavorite={toggleFavorite}
                  onToggleQueue={() => setShowQueue(!showQueue)}
                />

                {/* Sidebar content: relationship, session, observations, actions, settings, footer */}
                <RioSidebarContent
                  activityData={activityData}
                  onCollapse={() => setIsExpanded(false)}
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
