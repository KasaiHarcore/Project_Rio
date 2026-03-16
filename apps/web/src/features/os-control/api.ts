/**
 * OS Control API — shell execution, risk classification, session management.
 */

import { apiFetch } from "@/shared/api/client"
import type { ShellResult, ShellClassifyResult } from "./types"

export async function apiExecuteShell(
  command: string,
  options?: { working_directory?: string; timeout_seconds?: number },
): Promise<ShellResult> {
  return apiFetch<ShellResult>("/os/shell", {
    method: "POST",
    body: JSON.stringify({
      command,
      working_directory: options?.working_directory,
      timeout_seconds: options?.timeout_seconds ?? 30,
    }),
  })
}

export async function apiClassifyCommand(
  command: string,
): Promise<ShellClassifyResult> {
  return apiFetch<ShellClassifyResult>("/os/shell/classify", {
    method: "POST",
    body: JSON.stringify({ command }),
  })
}

export async function apiCloseShellSession(): Promise<void> {
  await apiFetch("/os/shell/session", { method: "DELETE" })
}
