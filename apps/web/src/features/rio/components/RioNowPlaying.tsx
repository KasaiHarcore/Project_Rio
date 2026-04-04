"use client"

import React, { useRef, useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart, Play, Pause, SkipForward, SkipBack, Volume2, VolumeX, Music, ListMusic, Shuffle, Repeat, Repeat1 } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMusicStore } from '@/features/music/store'
import type { Track } from '@/features/music/store'

function formatMusicTime(seconds: number): string {
  if (!seconds || !isFinite(seconds)) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export interface RioNowPlayingProps {
  currentTrack: Track | null
  tracks: Track[]
  isPlaying: boolean
  progress: number
  duration: number
  currentTime: number
  volume: number
  isMuted: boolean
  isShuffled: boolean
  repeatMode: 'off' | 'all' | 'one'
  favoriteIds: string[]
  showQueue: boolean
  onTogglePlayPause: () => void
  onNext: () => void
  onPrevious: () => void
  onSetVolume: (v: number) => void
  onToggleMute: () => void
  onToggleShuffle: () => void
  onSetRepeatMode: () => void
  onPlay: (track: Track) => void
  onSeek: (percent: number) => void
  onToggleFavorite: (trackId: string) => void
  onToggleQueue: () => void
}

export function RioNowPlaying({
  currentTrack, tracks, isPlaying, progress, duration, currentTime,
  volume, isMuted, isShuffled, repeatMode, favoriteIds, showQueue,
  onTogglePlayPause, onNext, onPrevious, onSetVolume, onToggleMute,
  onToggleShuffle, onSetRepeatMode,
  onPlay, onSeek, onToggleFavorite, onToggleQueue,
}: RioNowPlayingProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [artworkError, setArtworkError] = useState<string | null>(null)
  const addBlobTracks = useMusicStore(s => s.addBlobTracks)
  const isFavorited = currentTrack ? favoriteIds.includes(currentTrack.id) : false

  // Reset artwork error when track changes
  useEffect(() => {
    setArtworkError(null)
  }, [currentTrack?.id])

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const percent = ((e.clientX - rect.left) / rect.width) * 100
    onSeek(Math.max(0, Math.min(100, percent)))
  }

  const handleFileAdd = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    addBlobTracks(Array.from(files))
    e.target.value = ''
  }

  const isEmpty = tracks.length === 0

  return (
    <div>
      <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-3">
        Now Playing
      </h3>
      <div className="rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 overflow-hidden">
        {isEmpty ? (
          <div className="p-4 text-center">
            <Music size={24} className="text-indigo-400/30 mx-auto mb-2" />
            <p className="text-xs font-bold text-white/40 mb-1">No tracks loaded</p>
            <p className="text-[10px] text-white/25 mb-3">Drop files into public/music/ or add below</p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 text-xs font-bold text-indigo-300 transition-colors"
            >
              Add Music Files
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
        ) : (
        <>{/* Track info */}
        <div className="flex items-center gap-3 p-3">
          <div className="relative w-11 h-11 rounded-lg overflow-hidden bg-indigo-950/40 border border-white/[0.06] shrink-0 flex items-center justify-center">
            {currentTrack?.artworkUrl && !artworkError ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentTrack.artworkUrl}
                alt={currentTrack.name}
                className="absolute inset-0 w-full h-full object-cover"
                onError={() => setArtworkError(currentTrack.id)}
              />
            ) : currentTrack ? (
              <div className={cn(
                "absolute inset-0 flex items-center justify-center text-[13px] font-black text-white/60",
                "bg-gradient-to-br from-indigo-600/40 to-purple-600/40"
              )}>
                {currentTrack.name.charAt(0).toUpperCase()}
              </div>
            ) : (
              <Music size={16} className="text-indigo-400/40" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-white truncate">
              {currentTrack?.name ?? 'No track selected'}
            </p>
            <p className="text-[10px] text-white/30 truncate">
              {currentTrack?.fileName ?? `${tracks.length} tracks available`}
            </p>
          </div>
          <button
            onClick={() => currentTrack && onToggleFavorite(currentTrack.id)}
            className={cn(
              "shrink-0 transition-colors",
              isFavorited ? "text-rose-400" : "text-white/20 hover:text-rose-400"
            )}
          >
            <Heart size={14} fill={isFavorited ? "currentColor" : "none"} />
          </button>
        </div>

        {/* Progress */}
        <div className="px-3">
          <div
            onClick={handleProgressClick}
            className="h-1 bg-white/[0.08] rounded-full overflow-hidden cursor-pointer hover:h-1.5 transition-all"
          >
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-indigo-300 rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between mt-1 px-0.5">
            <span className="text-[9px] font-bold text-white/25">{formatMusicTime(currentTime)}</span>
            <span className="text-[9px] font-bold text-white/25">{formatMusicTime(duration)}</span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4 px-3 py-1.5">
          <button
            onClick={onToggleShuffle}
            className={cn("transition-colors", isShuffled ? "text-indigo-400" : "text-white/20 hover:text-white/50")}
            title="Shuffle"
          >
            <Shuffle size={14} />
          </button>
          <button onClick={onPrevious} className="text-white/40 hover:text-white transition-colors">
            <SkipBack size={16} fill="currentColor" />
          </button>
          <button
            onClick={onTogglePlayPause}
            className="w-9 h-9 rounded-full bg-white flex items-center justify-center hover:scale-105 transition-transform"
          >
            {isPlaying
              ? <Pause size={14} className="text-slate-900" fill="currentColor" />
              : <Play size={14} className="text-slate-900 ml-0.5" fill="currentColor" />
            }
          </button>
          <button onClick={onNext} className="text-white/40 hover:text-white transition-colors">
            <SkipForward size={16} fill="currentColor" />
          </button>
          <button
            onClick={onSetRepeatMode}
            className={cn("transition-colors", repeatMode !== 'off' ? "text-indigo-400" : "text-white/20 hover:text-white/50")}
            title={repeatMode === 'one' ? 'Repeat one' : repeatMode === 'all' ? 'Repeat all' : 'Repeat off'}
          >
            {repeatMode === 'one' ? <Repeat1 size={14} /> : <Repeat size={14} />}
          </button>
        </div>

        {/* Volume + Queue + Add */}
        <div className="flex items-center gap-2 px-3 pb-3 pt-1">
          <button onClick={onToggleMute} className="text-white/25 hover:text-white/60 transition-colors shrink-0">
            {isMuted || volume === 0 ? <VolumeX size={13} /> : <Volume2 size={13} />}
          </button>
          <input
            type="range"
            min={0} max={1} step={0.01}
            value={isMuted ? 0 : volume}
            onChange={e => onSetVolume(parseFloat(e.target.value))}
            className="flex-1 h-1 accent-indigo-400 cursor-pointer"
          />
          <button
            onClick={onToggleQueue}
            className={cn("shrink-0 transition-colors", showQueue ? "text-indigo-400" : "text-white/25 hover:text-white/60")}
            title="Track list"
          >
            <ListMusic size={13} />
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-white/25 hover:text-white/60 transition-colors shrink-0"
            title="Add music files"
          >
            <Music size={13} />
            <span className="sr-only">Add music</span>
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

        {/* Queue */}
        <AnimatePresence>
          {showQueue && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-white/[0.06]"
            >
              <div className="max-h-44 overflow-y-auto">
                {tracks.map((track, idx) => {
                  const isActive = currentTrack?.id === track.id
                  const isFav = favoriteIds.includes(track.id)
                  return (
                    <button
                      key={track.id}
                      onClick={() => onPlay(track)}
                      className={cn(
                        "w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors",
                        isActive ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
                      )}
                    >
                      <span className={cn("text-[10px] font-bold w-5 text-center shrink-0", isActive ? "text-indigo-400" : "text-white/20")}>
                        {isActive && isPlaying ? (
                          <span className="flex items-end justify-center gap-[1.5px] h-3">
                            <span className="w-[2px] bg-indigo-400 rounded-full animate-[bounce_0.5s_ease-in-out_infinite]" style={{ height: '50%' }} />
                            <span className="w-[2px] bg-indigo-400 rounded-full animate-[bounce_0.5s_ease-in-out_infinite_0.15s]" style={{ height: '100%' }} />
                            <span className="w-[2px] bg-indigo-400 rounded-full animate-[bounce_0.5s_ease-in-out_infinite_0.3s]" style={{ height: '50%' }} />
                          </span>
                        ) : (
                          String(idx + 1).padStart(2, '0')
                        )}
                      </span>
                      <span className={cn("text-[11px] font-bold truncate flex-1", isActive ? "text-indigo-300" : "text-white/60")}>
                        {track.name}
                      </span>
                      {isFav && <Heart size={10} className="text-rose-400 shrink-0" fill="currentColor" />}
                    </button>
                  )
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </>
      )}
      </div>
    </div>
  )
}
