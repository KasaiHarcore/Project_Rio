import type { Mission, MissionStatus, MissionStats } from './store'

const headers = { 'Content-Type': 'application/json' }

async function missionFetch<T>(
  path: string,
  opts?: RequestInit,
): Promise<T> {
  const res = await fetch(path, { headers, ...opts })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(body || `Mission API error: ${res.status}`)
  }
  if (res.status === 204) return null as T
  return (await res.json()) as T
}

export function apiListMissions(status?: MissionStatus): Promise<Mission[]> {
  const qs = status ? `?status=${status}` : ''
  return missionFetch<Mission[]>(`/api/missions${qs}`)
}

export function apiGetMissionStats(): Promise<MissionStats> {
  return missionFetch<MissionStats>('/api/missions/stats')
}

export function apiCreateMission(data: Partial<Mission>): Promise<Mission> {
  return missionFetch<Mission>('/api/missions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function apiUpdateMission(id: string, data: Partial<Mission>): Promise<Mission> {
  return missionFetch<Mission>(`/api/missions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteMission(id: string): Promise<void> {
  await missionFetch<void>(`/api/missions/${id}`, { method: 'DELETE' })
}

export function apiToggleStep(missionId: string, stepIndex: number): Promise<Mission> {
  return missionFetch<Mission>(
    `/api/missions/${missionId}/steps/${stepIndex}/toggle`,
    { method: 'PATCH' },
  )
}
