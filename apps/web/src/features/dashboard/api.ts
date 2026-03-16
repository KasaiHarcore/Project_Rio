import { apiFetch } from '@/shared/api/client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ThreadStat {
  id: string;
  title: string | null;
  status: string;
  progress: number;
  updated_at: string;
  message_count: number;
}

export interface DashboardStats {
  total_threads: number;
  active_threads: number;
  total_messages: number;
  total_documents: number;
  ready_documents: number;
  messages_today: number;
  messages_by_day: number[];
  recent_threads: ThreadStat[];
  onboarding_completed: boolean;
  level: number;
  total_xp: number;
  xp_in_level: number;
  xp_for_next: number;
}

export interface BriefingMission {
  id: string;
  title: string;
  deadline: string | null;
  progress: number;
}

export interface BriefingThread {
  id: string;
  title: string | null;
  updated_at: string;
}

export interface EmotionalStateData {
  mood: string;
  energy: number;
  affinity: number;
  relationship_tier: string;
  streak_days: number;
  interaction_count: number;
}

export interface SessionStats {
  sessions_this_week: number;
  total_messages_today: number;
  missions_completed_today: number;
  streak_days: number;
}

export interface SuggestedAction {
  label: string;
  action: string;
  target?: string | null;
}

export interface DashboardBriefing {
  briefing_text: string;
  urgent_missions: BriefingMission[];
  last_chats: BriefingThread[];
  emotional_state: EmotionalStateData;
  session_stats: SessionStats;
  suggested_actions: SuggestedAction[];
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiGetDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/dashboard/stats");
}

export async function apiGetBriefing(): Promise<DashboardBriefing> {
  return apiFetch<DashboardBriefing>("/dashboard/briefing");
}
