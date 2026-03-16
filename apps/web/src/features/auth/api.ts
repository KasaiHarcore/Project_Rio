import { apiFetch, setTokens, getAccessToken, clearTokens } from '@/shared/api/client'

// ── Types ──────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  success: boolean;
  user: UserProfile;
  tokens: AuthTokens;
}

// ── API ────────────────────────────────────────────────────────────────────

export async function apiLogin(
  username: string,
  password: string,
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
    noAuth: true,
  });
}

export async function apiRegister(
  username: string,
  email: string,
  password: string,
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
    noAuth: true,
  });
}

export async function apiGetMe(): Promise<{ success: boolean; user: UserProfile }> {
  return apiFetch("/auth/me");
}

export async function apiRefreshToken(
  refreshToken: string,
): Promise<{ success: boolean; access_token: string }> {
  return apiFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
    noAuth: true,
  });
}

export async function apiResetPassword(
  newPassword: string,
): Promise<{ success: boolean; message: string }> {
  return apiFetch("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      new_password: newPassword,
    }),
  });
}

export async function apiLogout(): Promise<void> {
  const accessToken = getAccessToken();
  const refreshMatch =
    typeof document !== "undefined"
      ? document.cookie.match(/(?:^|; )refresh-token=([^;]*)/)
      : null;
  const refreshToken = refreshMatch ? decodeURIComponent(refreshMatch[1]) : null;

  try {
    await apiFetch("/auth/logout", {
      method: "POST",
      body: JSON.stringify({
        access_token: accessToken,
        refresh_token: refreshToken,
      }),
    });
  } catch {
    // Best-effort — even if server call fails we still clear client tokens
  } finally {
    clearTokens();
  }
}

// Re-export token helpers for convenience
export { setTokens, getAccessToken, clearTokens } from '@/shared/api/client'
