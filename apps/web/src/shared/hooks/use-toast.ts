"use client"

import { create } from "zustand"

export type ToastVariant = "default" | "success" | "error" | "warning"

export interface Toast {
  id: string
  title: string
  description?: string
  variant?: ToastVariant
  duration?: number
}

interface ToastStore {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, "id">) => void
  removeToast: (id: string) => void
}

let toastCounter = 0

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = `toast-${++toastCounter}-${Date.now()}`
    set((state) => ({
      toasts: [...state.toasts, { id, variant: "default", duration: 4000, ...toast }],
    }))
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}))

/** Imperative toast function — call from anywhere */
export function toast(props: Omit<Toast, "id">) {
  useToastStore.getState().addToast(props)
}
