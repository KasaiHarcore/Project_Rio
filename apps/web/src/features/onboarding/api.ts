import { apiFetch } from '@/shared/api/client'

export interface OnboardingPayload {
  user_name?: string;
  specialization?: string;
  data_sources?: string[];
  agent_name?: string;
  tone?: string;
  directives?: string;
}

export async function apiSaveOnboarding(
  data: OnboardingPayload,
): Promise<{ success: boolean; onboarding_completed: boolean }> {
  return apiFetch("/onboarding", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
