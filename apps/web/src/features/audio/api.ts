const headers = { 'Content-Type': 'application/json' }

async function audioFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers, ...opts })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(body || `Audio API error: ${res.status}`)
  }
  if (res.status === 204) return null as T
  return (await res.json()) as T
}

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
  return audioFetch<AudioOverview[]>(`/api/audio?limit=${limit}&offset=${offset}`)
}

export function apiGetAudio(id: string): Promise<AudioOverview> {
  return audioFetch<AudioOverview>(`/api/audio/${id}`)
}

export function apiGenerateAudio(data: AudioGenerateRequest): Promise<AudioOverview> {
  return audioFetch<AudioOverview>('/api/audio', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteAudio(id: string): Promise<void> {
  await audioFetch<void>(`/api/audio/${id}`, { method: 'DELETE' })
}
