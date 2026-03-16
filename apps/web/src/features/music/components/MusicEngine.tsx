"use client"

import { useMusicPlayer } from '@/features/music/hooks/use-music-player'

/**
 * Headless component that drives the Howler audio engine.
 * Mount once in DashboardLayout so music persists across page navigation.
 */
export function MusicEngine() {
  useMusicPlayer()
  return null
}
