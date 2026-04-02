"use client"

import { useEffect, useCallback } from 'react'
import { Howl } from 'howler'
import { useMusicStore } from '@/features/music/store'

// ── Module-level singletons ──────────────────────────────────────────
let _howl: Howl | null = null
let _howlTrackId: string | null = null
let _raf = 0
let _seeking = false
let _hydrated = false

function getHowl() { return _howl }

// ── Hook ─────────────────────────────────────────────────────────────

export function useMusicPlayer() {
  const currentTrack = useMusicStore(s => s.currentTrack)
  const isPlaying = useMusicStore(s => s.isPlaying)
  const volume = useMusicStore(s => s.volume)
  const isMuted = useMusicStore(s => s.isMuted)

  const setProgress = useMusicStore(s => s.setProgress)
  const setDuration = useMusicStore(s => s.setDuration)
  const setCurrentTime = useMusicStore(s => s.setCurrentTime)
  const setIsLoading = useMusicStore(s => s.setIsLoading)
  const nextTrack = useMusicStore(s => s.nextTrack)
  const fetchTracks = useMusicStore(s => s.fetchTracks)
  const hydrateFromStorage = useMusicStore(s => s.hydrateFromStorage)

  // Progress update loop
  const updateProgress = useCallback(() => {
    const howl = getHowl()
    if (howl && howl.playing() && !_seeking) {
      const seek = howl.seek() as number
      const dur = howl.duration()
      if (dur > 0) {
        setCurrentTime(seek)
        setProgress((seek / dur) * 100)
      }
    }
    _raf = requestAnimationFrame(updateProgress)
  }, [setCurrentTime, setProgress])

  // Handle track changes — only create new Howl if track actually changed
  useEffect(() => {
    if (!currentTrack) return

    // Same track already loaded — don't recreate
    if (_howlTrackId === currentTrack.id && _howl) return

    // Different track — tear down old, build new
    if (_howl) {
      _howl.unload()
      _howl = null
    }

    _howlTrackId = currentTrack.id
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
        cancelAnimationFrame(_raf)
        _raf = requestAnimationFrame(updateProgress)
      },
      onend: () => {
        const state = useMusicStore.getState()
        if (state.repeatMode === 'one') {
          howl.seek(0)
          howl.play()
        } else {
          nextTrack()
        }
      },
      onseek: () => {
        _seeking = false
      },
    })

    _howl = howl

    if (isPlaying) {
      howl.play()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrack?.id])

  // Sync play/pause — also reconnects RAF on remount if already playing
  useEffect(() => {
    const howl = getHowl()
    if (!howl) return

    if (isPlaying && !howl.playing()) {
      howl.play()
    } else if (!isPlaying && howl.playing()) {
      howl.pause()
    }

    // Reconnect progress loop on remount
    if (isPlaying) {
      cancelAnimationFrame(_raf)
      _raf = requestAnimationFrame(updateProgress)
    }
  }, [isPlaying, updateProgress])

  // Sync volume
  useEffect(() => {
    const howl = getHowl()
    if (!howl) return
    howl.volume(isMuted ? 0 : volume)
  }, [volume, isMuted])

  // Handle seek from store
  useEffect(() => {
    const unsub = useMusicStore.subscribe((state, prev) => {
      const howl = getHowl()
      if (!howl) return

      const dur = howl.duration()
      if (dur > 0 && state.currentTime !== prev.currentTime) {
        const howlSeek = howl.seek() as number
        const diff = Math.abs(howlSeek - state.currentTime)
        if (diff > 1) {
          _seeking = true
          howl.seek(state.currentTime)
        }
      }
    })
    return unsub
  }, [])

  // Hydrate + fetch on mount
  useEffect(() => {
    const state = useMusicStore.getState()
    // Always hydrate preferences; fetch tracks if store is empty or first time
    if (!_hydrated) {
      _hydrated = true
      hydrateFromStorage()
    }
    if (state.tracks.length === 0) {
      fetchTracks()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // On remount: sync store progress with existing Howl position
  useEffect(() => {
    const howl = getHowl()
    if (howl && howl.duration() > 0) {
      const seek = howl.seek() as number
      const dur = howl.duration()
      setCurrentTime(seek)
      setProgress((seek / dur) * 100)
      setDuration(dur)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Cleanup: only stop RAF, never unload the Howl
  useEffect(() => {
    return () => {
      cancelAnimationFrame(_raf)
    }
  }, [])
}
