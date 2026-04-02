"use client"

import React, { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, SkipForward, SkipBack, Volume2, VolumeX, Repeat, Repeat1, Heart, Zap, Shuffle, Plus, Music } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMusicStore } from '@/features/music/store'
import Image from 'next/image'

function formatTime(seconds: number): string {
    if (!seconds || !isFinite(seconds)) return '0:00'
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
}

export function SystemOperationPlayer() {
    // Audio engine is driven by MusicEngine in DashboardLayout — this is UI only.

    const tracks = useMusicStore(s => s.tracks)
    const currentTrack = useMusicStore(s => s.currentTrack)
    const isPlaying = useMusicStore(s => s.isPlaying)
    const progress = useMusicStore(s => s.progress)
    const duration = useMusicStore(s => s.duration)
    const currentTime = useMusicStore(s => s.currentTime)
    const volume = useMusicStore(s => s.volume)
    const isMuted = useMusicStore(s => s.isMuted)
    const repeatMode = useMusicStore(s => s.repeatMode)
    const isShuffled = useMusicStore(s => s.isShuffled)
    const favoriteIds = useMusicStore(s => s.favoriteIds)

    const togglePlayPause = useMusicStore(s => s.togglePlayPause)
    const nextTrack = useMusicStore(s => s.nextTrack)
    const previousTrack = useMusicStore(s => s.previousTrack)
    const setVolume = useMusicStore(s => s.setVolume)
    const toggleMute = useMusicStore(s => s.toggleMute)
    const setRepeatMode = useMusicStore(s => s.setRepeatMode)
    const toggleShuffle = useMusicStore(s => s.toggleShuffle)
    const seekTo = useMusicStore(s => s.seekTo)
    const toggleFavorite = useMusicStore(s => s.toggleFavorite)
    const addBlobTracks = useMusicStore(s => s.addBlobTracks)

    const [showVolume, setShowVolume] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const progressBarRef = useRef<HTMLDivElement>(null)

    const avatarSrc = '/images/avatar.png'

    const isFavorited = currentTrack ? favoriteIds.includes(currentTrack.id) : false
    const isEmpty = tracks.length === 0

    const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
        const bar = progressBarRef.current
        if (!bar) return
        const rect = bar.getBoundingClientRect()
        const percent = ((e.clientX - rect.left) / rect.width) * 100
        seekTo(Math.max(0, Math.min(100, percent)))
    }

    const handleFileAdd = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files
        if (!files || files.length === 0) return
        addBlobTracks(Array.from(files))
        e.target.value = ''
    }

    return (
        <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.5 }}
            className="w-full ptr-none"
        >
            <div className="w-full flex flex-col bg-[#050505]/95 backdrop-blur-[64px] backdrop-saturate-[200%] border border-white/10 rounded-[28px] shadow-[0_20px_60px_rgba(0,0,0,0.9)] pointer-events-auto overflow-hidden relative z-[100]">

                {/* SYS LOG Ticker */}
                <div className="w-full flex items-center bg-black/60 border-b border-white/5 px-4 py-1.5">
                    <span className="text-[8px] font-black text-emerald-400 uppercase tracking-widest shrink-0 mr-3 border border-emerald-500/30 px-1.5 py-0.5 rounded bg-emerald-500/10 flex items-center gap-1">
                        <Zap size={8} /> SYS LOG
                    </span>
                    <div
                        className="flex-1 overflow-hidden relative"
                        style={{ maskImage: 'linear-gradient(to right, transparent, black 2%, black 98%, transparent)', WebkitMaskImage: 'linear-gradient(to right, transparent, black 2%, black 98%, transparent)' }}
                    >
                        <motion.div
                            animate={{ x: ["50%", "-100%"] }}
                            transition={{ repeat: Infinity, duration: 25, ease: "linear" }}
                            className="whitespace-nowrap text-[10px] font-mono text-emerald-400/80 tracking-tight"
                        >
                            {`[PROTOCOL INITIALIZED] Establishing secure connection to local environment... [OK] /// [MONITOR] Focus rate steady at 85%. Proceeding with background memory indexing. /// [ANALYSIS] Anticipating logic requirements... simulating 14,000 architecture failure points... 0 detected. /// [DEFENSE] 3 unauthorized background notification attempts blocked. ///`}
                        </motion.div>
                    </div>
                </div>

                <div className="flex items-center justify-between gap-4 px-6 py-3">
                    {/* Left: Now Playing */}
                    <div className="flex items-center gap-4 w-[280px] shrink-0">
                        <div className="relative w-12 h-12 rounded-xl overflow-hidden bg-indigo-950/50 border border-white/10 flex items-center justify-center">
                            <Image src={avatarSrc} alt="Operation Monitor" fill className="object-contain p-1" />
                            <div className="absolute inset-0 bg-indigo-500/20 mix-blend-screen" />
                        </div>
                        <div className="flex-1 min-w-0">
                            {isEmpty ? (
                                <>
                                    <h4 className="text-sm font-bold text-indigo-200/40 truncate flex items-center gap-1.5">
                                        <Music size={14} /> No Tracks
                                    </h4>
                                    <p className="text-[10px] text-indigo-200/30 truncate">
                                        Drop files into public/music/
                                    </p>
                                </>
                            ) : (
                                <>
                                    <h4 className="text-sm font-bold text-white truncate">
                                        {currentTrack?.name ?? 'Select a track'}
                                    </h4>
                                    <p className="text-xs text-indigo-200/60 truncate flex items-center gap-1">
                                        <Zap size={10} className="text-amber-400" />
                                        {currentTrack ? currentTrack.fileName : `${tracks.length} tracks loaded`}
                                    </p>
                                </>
                            )}
                        </div>
                        <button
                            onClick={() => currentTrack && toggleFavorite(currentTrack.id)}
                            className={cn(
                                "transition-colors",
                                isFavorited
                                    ? "text-rose-400 hover:text-rose-300"
                                    : "text-indigo-200/40 hover:text-rose-400"
                            )}
                        >
                            <Heart size={16} fill={isFavorited ? "currentColor" : "none"} />
                        </button>
                    </div>

                    {/* Center: Controls & Progress */}
                    <div className="flex-1 max-w-2xl flex flex-col items-center gap-2">
                        <div className="flex items-center gap-6">
                            <button
                                onClick={toggleShuffle}
                                className={cn(
                                    "transition-colors",
                                    isShuffled ? "text-indigo-400" : "text-indigo-200/40 hover:text-white"
                                )}
                            >
                                <Shuffle size={16} />
                            </button>
                            <button
                                onClick={previousTrack}
                                className="text-indigo-200/70 hover:text-white transition-colors"
                            >
                                <SkipBack size={20} fill="currentColor" />
                            </button>
                            <button
                                onClick={togglePlayPause}
                                className="w-10 h-10 rounded-full bg-white text-indigo-950 flex items-center justify-center hover:scale-105 transition-transform"
                            >
                                {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
                            </button>
                            <button
                                onClick={nextTrack}
                                className="text-indigo-200/70 hover:text-white transition-colors"
                            >
                                <SkipForward size={20} fill="currentColor" />
                            </button>
                            <button
                                onClick={setRepeatMode}
                                className={cn(
                                    "transition-colors relative",
                                    repeatMode !== 'off' ? "text-indigo-400" : "text-indigo-200/40 hover:text-white"
                                )}
                            >
                                {repeatMode === 'one' ? <Repeat1 size={16} /> : <Repeat size={16} />}
                            </button>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full flex items-center gap-3">
                            <span className="text-[10px] font-bold text-indigo-200/50 w-8 text-right">
                                {formatTime(currentTime)}
                            </span>

                            <div
                                ref={progressBarRef}
                                onClick={handleProgressClick}
                                className="relative h-1 flex-1 bg-white/10 rounded-full overflow-hidden group/bar cursor-pointer hover:h-2 transition-all"
                            >
                                <div
                                    className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-indigo-500 to-indigo-300 rounded-full"
                                    style={{ width: `${progress}%` }}
                                />
                                <div
                                    className="absolute top-0 bottom-0 left-0 bg-white opacity-0 group-hover/bar:opacity-20 transition-opacity"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>

                            <span className="text-[10px] font-bold text-indigo-200/50 w-8">
                                {formatTime(duration)}
                            </span>
                        </div>
                    </div>

                    {/* Right: Volume + Add */}
                    <div className="flex items-center justify-end gap-3 w-[280px] shrink-0">
                        <div
                            className="flex items-center gap-2 relative"
                            onMouseEnter={() => setShowVolume(true)}
                            onMouseLeave={() => setShowVolume(false)}
                        >
                            <button
                                onClick={toggleMute}
                                className="text-indigo-200/60 hover:text-white transition-colors"
                            >
                                {isMuted || volume === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}
                            </button>
                            {showVolume && (
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    value={isMuted ? 0 : volume}
                                    onChange={e => setVolume(parseFloat(e.target.value))}
                                    className="w-20 h-1 accent-indigo-400 cursor-pointer"
                                />
                            )}
                        </div>
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="text-indigo-200/60 hover:text-white transition-colors"
                            title="Add music files"
                        >
                            <Plus size={16} />
                        </button>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="audio/*"
                            multiple
                            className="hidden"
                            onChange={handleFileAdd}
                        />
                    </div>
                </div>

            </div>
        </motion.div>
    )
}
