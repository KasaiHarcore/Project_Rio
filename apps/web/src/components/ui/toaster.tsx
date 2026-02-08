"use client"

import React, { useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react"
import { useToastStore, type ToastVariant } from "@/hooks/use-toast"

const variantConfig: Record<ToastVariant, { icon: React.ElementType; className: string }> = {
  default: {
    icon: Info,
    className: "bg-[var(--surface-elevated)] border-border text-foreground",
  },
  success: {
    icon: CheckCircle2,
    className: "bg-[var(--surface-elevated)] border-emerald-500/30 text-foreground",
  },
  error: {
    icon: AlertCircle,
    className: "bg-[var(--surface-elevated)] border-destructive/30 text-foreground",
  },
  warning: {
    icon: AlertTriangle,
    className: "bg-[var(--surface-elevated)] border-yellow-500/30 text-foreground",
  },
}

const iconColors: Record<ToastVariant, string> = {
  default: "text-primary",
  success: "text-emerald-500",
  error: "text-destructive",
  warning: "text-yellow-500",
}

function ToastItem({ id, title, description, variant = "default", duration = 4000 }: {
  id: string
  title: string
  description?: string
  variant?: ToastVariant
  duration?: number
}) {
  const removeToast = useToastStore((s) => s.removeToast)
  const config = variantConfig[variant]
  const Icon = config.icon

  useEffect(() => {
    const timer = setTimeout(() => removeToast(id), duration)
    return () => clearTimeout(timer)
  }, [id, duration, removeToast])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-xl min-w-[300px] max-w-[420px] ${config.className}`}
    >
      <Icon size={18} className={`mt-0.5 flex-shrink-0 ${iconColors[variant]}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold leading-tight">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{description}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(id)}
        className="flex-shrink-0 p-1 rounded-lg transition-colors text-muted-foreground hover:text-foreground hover:bg-muted"
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </motion.div>
  )
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts)

  return (
    <div
      className="fixed bottom-4 right-4 z-[200] flex flex-col-reverse gap-2 pointer-events-none"
      aria-live="polite"
      aria-label="Notifications"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <ToastItem key={t.id} {...t} />
        ))}
      </AnimatePresence>
    </div>
  )
}
