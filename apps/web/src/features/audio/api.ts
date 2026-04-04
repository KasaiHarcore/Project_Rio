import { apiFetch } from '@/shared/api/client'

export interface AudioOverview {
  id: string
  user_id: string
  title: string
  source_ids: string[]
  source_type: string
  transcript: string | null
  audio_path: string | null
  duration_seconds: number | null
  format: string
  status: 'pending' | 'generating' | 'ready' | 'failed'
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface AudioGenerateRequest {
  source_ids: string[]
  source_type: string
  format: string
  title?: string
}

export function apiListAudio(limit = 20, offset = 0): Promise<AudioOverview[]> {
  return apiFetch<AudioOverview[]>(`/audio?limit=${limit}&offset=${offset}`)
}

export function apiGetAudio(id: string): Promise<AudioOverview> {
  return apiFetch<AudioOverview>(`/audio/${id}`)
}

export function apiGenerateAudio(data: AudioGenerateRequest): Promise<AudioOverview> {
  return apiFetch<AudioOverview>('/audio/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteAudio(id: string): Promise<void> {
  await apiFetch(`/audio/${id}`, { method: 'DELETE' })
}

/**
 * Build the audio stream URL.
 * Uses the Next.js proxy route because <audio src> cannot set Authorization headers.
 */
export function getAudioStreamUrl(id: string): string {
  return `/api/audio/${id}/stream`
}
