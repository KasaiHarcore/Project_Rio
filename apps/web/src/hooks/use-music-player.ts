"use client"

import { useEffect, useRef, useCallback } from 'react'
import { Howl } from 'howler'
import { useMusicStore } from '@/store/music-store'

export function useMusicPlayer() {
  const howlRef = useRef<Howl | null>(null)
  const rafRef = useRef<number>(0)
  const seekingRef = useRef(false)

  const currentTrack = useMusicStore(s => s.currentTrack)
  const isPlaying = useMusicStore(s => s.isPlaying)
  const volume = useMusicStore(s => s.volume)
  const isMuted = useMusicStore(s => s.isMuted)
  const repeatMode = useMusicStore(s => s.repeatMode)

  const setProgress = useMusicStore(s => s.setProgress)
  const setDuration = useMusicStore(s => s.setDuration)
  const setCurrentTime = useMusicStore(s => s.setCurrentTime)
  const setIsLoading = useMusicStore(s => s.setIsLoading)
  const nextTrack = useMusicStore(s => s.nextTrack)
  const play = useMusicStore(s => s.play)
  const fetchTracks = useMusicStore(s => s.fetchTracks)
  const hydrateFromStorage = useMusicStore(s => s.hydrateFromStorage)

  // Progress update loop
  const updateProgress = useCallback(() => {
    const howl = howlRef.current
    if (howl && howl.playing() && !seekingRef.current) {
      const seek = howl.seek() as number
      const dur = howl.duration()
      if (dur > 0) {
        setCurrentTime(seek)
        setProgress((seek / dur) * 100)
      }
    }
    rafRef.current = requestAnimationFrame(updateProgress)
  }, [setCurrentTime, setProgress])

  // Handle track changes — create new Howl
  useEffect(() => {
    // Cleanup old
    if (howlRef.current) {
      howlRef.current.unload()
      howlRef.current = null
    }

    if (!currentTrack) return

    setIsLoading(true)

    const howl = new Howl({
      src: [currentTrack.url],
      html5: true,
      volume: isMuted ? 0 : volume,
      onload: () => {
        setDuration(howl.duration())
        setIsLoading(false)
      },
      onloaderror: () => {
        setIsLoading(false)
      },
      onplay: () => {
        // Start progress loop
        cancelAnimationFrame(rafRef.current)
        rafRef.current = requestAnimationFrame(updateProgress)
      },
      onend: () => {
        // Auto-advance
        const state = useMusicStore.getState()
        if (state.repeatMode === 'one') {
          howl.seek(0)
          howl.play()
        } else {
          nextTrack()
        }
      },
      onseek: () => {
        seekingRef.current = false
      },
    })

    howlRef.current = howl

    // Auto-play if isPlaying
    if (isPlaying) {
      howl.play()
    }

    return () => {
      cancelAnimationFrame(rafRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrack?.id])

  // Sync play/pause state
  useEffect(() => {
    const howl = howlRef.current
    if (!howl) return

    if (isPlaying && !howl.playing()) {
      howl.play()
    } else if (!isPlaying && howl.playing()) {
      howl.pause()
    }
  }, [isPlaying])

  // Sync volume
  useEffect(() => {
    const howl = howlRef.current
    if (!howl) return
    howl.volume(isMuted ? 0 : volume)
  }, [volume, isMuted])

  // Handle seek from store
  useEffect(() => {
    const unsub = useMusicStore.subscribe((state, prev) => {
      const howl = howlRef.current
      if (!howl) return

      // Detect seekTo calls: progress changed but not from our RAF loop
      const dur = howl.duration()
      if (dur > 0 && state.currentTime !== prev.currentTime) {
        const howlSeek = howl.seek() as number
        const diff = Math.abs(howlSeek - state.currentTime)
        if (diff > 1) {
          seekingRef.current = true
          howl.seek(state.currentTime)
        }
      }
    })
    return unsub
  }, [])

  // Hydrate + fetch on mount
  useEffect(() => {
    hydrateFromStorage()
    fetchTracks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAnimationFrame(rafRef.current)
      if (howlRef.current) {
        howlRef.current.unload()
        howlRef.current = null
      }
    }
  }, [])
}
