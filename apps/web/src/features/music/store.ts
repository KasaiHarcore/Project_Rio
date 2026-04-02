import { create } from 'zustand'

/* ─── Types ──────────────────────────────────────────────────────── */

export interface Track {
  id: string
  name: string
  fileName: string
  url: string
  /** URL to embedded album artwork (served by /api/music/artwork) */
  artworkUrl?: string
  /** Blob tracks added via file picker (session-only) */
  blob?: boolean
}

export type RepeatMode = 'off' | 'all' | 'one'

/* ─── Store ──────────────────────────────────────────────────────── */

interface MusicState {
  tracks: Track[]
  currentTrack: Track | null
  currentIndex: number
  isPlaying: boolean
  volume: number
  isMuted: boolean
  isLoading: boolean
  repeatMode: RepeatMode
  isShuffled: boolean
  shuffleOrder: number[]
  progress: number
  duration: number
  currentTime: number
  musicDir: string
  favoriteIds: string[]

  // Actions
  fetchTracks: () => Promise<void>
  play: (track?: Track) => void
  pause: () => void
  togglePlayPause: () => void
  nextTrack: () => void
  previousTrack: () => void
  setVolume: (v: number) => void
  toggleMute: () => void
  setRepeatMode: () => void
  toggleShuffle: () => void
  seekTo: (percent: number) => void
  setProgress: (p: number) => void
  setDuration: (d: number) => void
  setCurrentTime: (t: number) => void
  setIsLoading: (l: boolean) => void
  toggleFavorite: (trackId: string) => void
  setMusicDir: (path: string) => Promise<void>
  addBlobTracks: (files: File[]) => void
  hydrateFromStorage: () => void
}

function generateShuffleOrder(length: number, currentIndex: number): number[] {
  const indices = Array.from({ length }, (_, i) => i).filter(i => i !== currentIndex)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[indices[i], indices[j]] = [indices[j], indices[i]]
  }
  return [currentIndex, ...indices]
}

function persist(key: string, value: string) {
  try { localStorage.setItem(key, value) } catch { /* noop */ }
}

function load(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

export const useMusicStore = create<MusicState>((set, get) => ({
  tracks: [],
  currentTrack: null,
  currentIndex: -1,
  isPlaying: false,
  volume: 0.7,
  isMuted: false,
  isLoading: false,
  repeatMode: 'off' as RepeatMode,
  isShuffled: false,
  shuffleOrder: [],
  progress: 0,
  duration: 0,
  currentTime: 0,
  musicDir: '',
  favoriteIds: [],

  fetchTracks: async () => {
    try {
      set({ isLoading: true })
      const res = await fetch('/api/music')
      const data = await res.json()
      const apiTracks: Track[] = data.tracks ?? []
      const existing = get().tracks.filter(t => t.blob)
      const merged = [...apiTracks, ...existing]
      set({ tracks: merged, musicDir: data.musicDir ?? '', isLoading: false })
      const lastId = load('rio-music-last-track')
      if (lastId && !get().currentTrack) {
        const idx = merged.findIndex(t => t.id === lastId)
        if (idx >= 0) set({ currentTrack: merged[idx], currentIndex: idx })
      }
    } catch {
      set({ isLoading: false })
    }
  },

  play: (track) => {
    const state = get()
    if (track) {
      const idx = state.tracks.findIndex(t => t.id === track.id)
      persist('rio-music-last-track', track.id)
      set({ currentTrack: track, currentIndex: idx >= 0 ? idx : 0, isPlaying: true })
      if (state.isShuffled) {
        set({ shuffleOrder: generateShuffleOrder(state.tracks.length, idx >= 0 ? idx : 0) })
      }
    } else if (state.currentTrack) {
      set({ isPlaying: true })
    } else if (state.tracks.length > 0) {
      const first = state.tracks[0]
      persist('rio-music-last-track', first.id)
      set({ currentTrack: first, currentIndex: 0, isPlaying: true })
    }
  },

  pause: () => set({ isPlaying: false }),

  togglePlayPause: () => {
    const state = get()
    if (state.isPlaying) {
      set({ isPlaying: false })
    } else {
      get().play()
    }
  },

  nextTrack: () => {
    const { tracks, currentIndex, isShuffled, shuffleOrder, repeatMode } = get()
    if (tracks.length === 0) return
    if (repeatMode === 'one') {
      set({ progress: 0, currentTime: 0 })
      get().play()
      return
    }
    let nextIdx: number
    if (isShuffled && shuffleOrder.length > 0) {
      const shufflePos = shuffleOrder.indexOf(currentIndex)
      const nextShufflePos = shufflePos + 1
      if (nextShufflePos >= shuffleOrder.length) {
        if (repeatMode === 'all') {
          const newOrder = generateShuffleOrder(tracks.length, shuffleOrder[0])
          set({ shuffleOrder: newOrder })
          nextIdx = newOrder[0]
        } else {
          set({ isPlaying: false })
          return
        }
      } else {
        nextIdx = shuffleOrder[nextShufflePos]
      }
    } else {
      nextIdx = currentIndex + 1
      if (nextIdx >= tracks.length) {
        if (repeatMode === 'all') {
          nextIdx = 0
        } else {
          set({ isPlaying: false })
          return
        }
      }
    }
    const t = tracks[nextIdx]
    persist('rio-music-last-track', t.id)
    set({ currentTrack: t, currentIndex: nextIdx, isPlaying: true, progress: 0, currentTime: 0 })
  },

  previousTrack: () => {
    const { tracks, currentIndex, currentTime, isShuffled, shuffleOrder } = get()
    if (tracks.length === 0) return
    if (currentTime > 3) {
      set({ progress: 0, currentTime: 0 })
      return
    }
    let prevIdx: number
    if (isShuffled && shuffleOrder.length > 0) {
      const shufflePos = shuffleOrder.indexOf(currentIndex)
      prevIdx = shufflePos > 0 ? shuffleOrder[shufflePos - 1] : shuffleOrder[shuffleOrder.length - 1]
    } else {
      prevIdx = currentIndex - 1
      if (prevIdx < 0) prevIdx = tracks.length - 1
    }
    const t = tracks[prevIdx]
    persist('rio-music-last-track', t.id)
    set({ currentTrack: t, currentIndex: prevIdx, isPlaying: true, progress: 0, currentTime: 0 })
  },

  setVolume: (v) => {
    persist('rio-music-volume', String(v))
    set({ volume: v, isMuted: v === 0 })
  },

  toggleMute: () => set(s => ({ isMuted: !s.isMuted })),

  setRepeatMode: () => {
    const modes: RepeatMode[] = ['off', 'all', 'one']
    const current = get().repeatMode
    const next = modes[(modes.indexOf(current) + 1) % modes.length]
    persist('rio-music-repeat', next)
    set({ repeatMode: next })
  },

  toggleShuffle: () => {
    const { isShuffled, tracks, currentIndex } = get()
    if (!isShuffled) {
      set({ isShuffled: true, shuffleOrder: generateShuffleOrder(tracks.length, currentIndex) })
    } else {
      set({ isShuffled: false, shuffleOrder: [] })
    }
  },

  seekTo: (percent) => {
    const duration = get().duration
    set({ progress: percent, currentTime: (percent / 100) * duration })
  },

  setProgress: (p) => set({ progress: p }),
  setDuration: (d) => set({ duration: d }),
  setCurrentTime: (t) => set({ currentTime: t }),
  setIsLoading: (l) => set({ isLoading: l }),

  toggleFavorite: (trackId) => {
    const favs = get().favoriteIds
    const next = favs.includes(trackId)
      ? favs.filter(id => id !== trackId)
      : [...favs, trackId]
    persist('rio-music-favorites', JSON.stringify(next))
    set({ favoriteIds: next })
  },

  setMusicDir: async (dirPath) => {
    try {
      set({ isLoading: true })
      persist('rio-music-dir', dirPath)
      const res = await fetch('/api/music', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ musicDir: dirPath }),
      })
      const data = await res.json()
      if (res.ok) {
        const existing = get().tracks.filter(t => t.blob)
        set({ tracks: [...(data.tracks ?? []), ...existing], musicDir: data.musicDir ?? dirPath, isLoading: false })
      } else {
        set({ isLoading: false })
      }
    } catch {
      set({ isLoading: false })
    }
  },

  addBlobTracks: (files) => {
    const newTracks: Track[] = files.map(file => ({
      id: `blob-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' '),
      fileName: file.name,
      url: URL.createObjectURL(file),
      blob: true,
    }))
    set(s => ({ tracks: [...s.tracks, ...newTracks] }))
  },

  hydrateFromStorage: () => {
    if (typeof window === 'undefined') return
    const vol = load('rio-music-volume')
    const favs = load('rio-music-favorites')
    const repeat = load('rio-music-repeat')
    const dir = load('rio-music-dir')

    set({
      ...(vol !== null ? { volume: parseFloat(vol) } : {}),
      ...(favs !== null ? { favoriteIds: JSON.parse(favs) } : {}),
      ...(repeat !== null ? { repeatMode: repeat as RepeatMode } : {}),
      ...(dir !== null ? { musicDir: dir } : {}),
    })
  },
}))
