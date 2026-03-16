"use client"

import React, { useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { cn } from "@/shared/lib/utils"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps {
  className?: string
  children: React.ReactNode
  /** Show the close button in the top-right corner */
  showClose?: boolean
  onClose?: () => void
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false)
    },
    [onOpenChange]
  )

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleEscape)
      document.body.style.overflow = "hidden"
    }
    return () => {
      document.removeEventListener("keydown", handleEscape)
      document.body.style.overflow = ""
    }
  }, [open, handleEscape])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => onOpenChange(false)}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
          />
          {/* Content wrapper */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            {children}
          </div>
        </>
      )}
    </AnimatePresence>
  )
}

export function DialogContent({ className, children, showClose = true, onClose }: DialogContentProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 10 }}
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      className={cn(
        "pointer-events-auto relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl",
        className
      )}
    >
      {showClose && onClose && (
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Close dialog"
        >
          <X size={16} />
        </button>
      )}
      {children}
    </motion.div>
  )
}
