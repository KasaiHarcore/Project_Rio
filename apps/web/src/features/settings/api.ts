import { apiFetch } from '@/shared/api/client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ApiKeyStatus {
  openai_configured: boolean;
  openrouter_configured: boolean;
  tavily_configured: boolean;
  cohere_configured: boolean;
  openai_masked?: string;
  openrouter_masked?: string;
  tavily_masked?: string;
  cohere_masked?: string;
}

export interface UserSettings {
  id: string;
  user_id: string;
  api_keys?: ApiKeyStatus;
  temperature: number;
  max_tokens?: number | null;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
  system_prompt: string | null;
  model_name: string;
  max_iterations: number;
  top_k: number;
  enable_planner: boolean;
  enable_reflection: boolean;
  enable_input_guardrail: boolean;
  enable_output_guardrail: boolean;
  enable_phoenix_tracing: boolean;
  phoenix_project: string | null;
  mission_reminders: boolean;
  chat_alerts: boolean;
  system_updates: boolean;
  weekly_summary: boolean;
  error_alerts: boolean;
  sound_enabled: boolean;
  email_notifications: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfileData {
  id: string;
  user_id: string;
  full_name: string | null;
  phone: string | null;
  address: string | null;
  company: string | null;
  job_title: string | null;
  locale: string | null;
  specialization: string | null;
  agent_name: string | null;
  tone: string | null;
  directives: string | null;
  data_sources: string[] | null;
  onboarding_completed: boolean;
  bio: string | null;
  study_goal: string | null;
  created_at: string;
  updated_at: string;
}

export interface SettingsResponse {
  success: boolean;
  settings: UserSettings;
  profile: UserProfileData | null;
}

export interface UserSettingsUpdate {
  openai_api_key?: string;
  openrouter_api_key?: string;
  tavily_api_key?: string;
  cohere_api_key?: string;
  temperature?: number;
  max_tokens?: number | null;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
  system_prompt?: string | null;
  model_name?: string;
  max_iterations?: number;
  top_k?: number;
  enable_planner?: boolean;
  enable_reflection?: boolean;
  enable_input_guardrail?: boolean;
  enable_output_guardrail?: boolean;
  enable_phoenix_tracing?: boolean;
  phoenix_project?: string | null;
  mission_reminders?: boolean;
  chat_alerts?: boolean;
  system_updates?: boolean;
  weekly_summary?: boolean;
  error_alerts?: boolean;
  sound_enabled?: boolean;
  email_notifications?: boolean;
}

export interface UserProfileUpdateData {
  full_name?: string;
  bio?: string;
  study_goal?: string;
  phone?: string;
  address?: string;
  company?: string;
  job_title?: string;
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiGetSettings(): Promise<SettingsResponse> {
  return apiFetch<SettingsResponse>("/settings");
}

export async function apiUpdateSettings(
  updates: UserSettingsUpdate,
): Promise<SettingsResponse> {
  return apiFetch<SettingsResponse>("/settings", {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function apiUpdateProfile(
  updates: UserProfileUpdateData,
): Promise<{ success: boolean; message: string }> {
  return apiFetch("/settings/profile", {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function apiUpdateUserInfo(data: {
  username?: string;
  email?: string;
}): Promise<{ success: boolean; message: string }> {
  return apiFetch("/settings/user-info", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
