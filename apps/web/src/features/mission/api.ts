import { apiFetch } from '@/shared/api/client'
import type { Mission, MissionStatus, MissionStats } from './store'

export function apiListMissions(status?: MissionStatus): Promise<Mission[]> {
  const qs = status ? `?status=${status}` : ''
  return apiFetch<Mission[]>(`/missions${qs}`)
}

export function apiGetMissionStats(): Promise<MissionStats> {
  return apiFetch<MissionStats>('/missions/stats')
}

export function apiCreateMission(data: Partial<Mission>): Promise<Mission> {
  return apiFetch<Mission>('/missions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function apiUpdateMission(id: string, data: Partial<Mission>): Promise<Mission> {
  return apiFetch<Mission>(`/missions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteMission(id: string): Promise<void> {
  await apiFetch(`/missions/${id}`, { method: 'DELETE' })
}

export function apiToggleStep(missionId: string, stepIndex: number): Promise<Mission> {
  return apiFetch<Mission>(
    `/missions/${missionId}/steps/${stepIndex}/toggle`,
    { method: 'PATCH' },
  )
}
