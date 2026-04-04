import { apiFetch } from '@/shared/api/client'

export interface Automation {
  id: string
  user_id: string
  name: string
  description: string | null
  cron_expression: string
  timezone: string
  agent_instruction: string
  agent_mode: string
  result_delivery: string
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  run_count: number
  max_runs: number | null
  last_result: {
    answer?: string
    thread_id?: string
    executed_at?: string
    delivery?: string
    delivered_note_id?: string
    delivered_thread_id?: string
    delivery_error?: string
  } | null
  created_at: string
  updated_at: string
}

export interface AutomationCreate {
  name: string
  description?: string
  cron_expression: string
  timezone?: string
  agent_instruction: string
  agent_mode?: string
  result_delivery?: string
  max_runs?: number | null
}

export interface AutomationUpdate {
  name?: string
  description?: string
  cron_expression?: string
  timezone?: string
  agent_instruction?: string
  agent_mode?: string
  result_delivery?: string
  enabled?: boolean
  max_runs?: number | null
}

export function apiListAutomations(): Promise<Automation[]> {
  return apiFetch<Automation[]>('/automations')
}

export function apiGetAutomation(id: string): Promise<Automation> {
  return apiFetch<Automation>(`/automations/${id}`)
}

export function apiCreateAutomation(data: AutomationCreate): Promise<Automation> {
  return apiFetch<Automation>('/automations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function apiUpdateAutomation(id: string, data: AutomationUpdate): Promise<Automation> {
  return apiFetch<Automation>(`/automations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function apiDeleteAutomation(id: string): Promise<void> {
  await apiFetch(`/automations/${id}`, { method: 'DELETE' })
}

export function apiRunAutomation(id: string): Promise<{ success: boolean; answer: string }> {
  return apiFetch<{ success: boolean; answer: string }>(`/automations/${id}/run`, {
    method: 'POST',
  })
}
