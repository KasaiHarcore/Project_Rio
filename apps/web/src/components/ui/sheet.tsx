"use client"

import React, { useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { cn } from "@/shared/lib/utils"

type SheetSide = "left" | "right"

interface SheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  side?: SheetSide
  children: React.ReactNode
  className?: string
}

const slideVariants = {
  left: {
    initial: { x: "-100%" },
    animate: { x: 0 },
    exit: { x: "-100%" },
  },
  right: {
    initial: { x: "100%" },
    animate: { x: 0 },
    exit: { x: "100%" },
  },
}

export function Sheet({ open, onOpenChange, side = "left", children, className }: SheetProps) {
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

          {/* Panel */}
          <motion.div
            initial={slideVariants[side].initial}
            animate={slideVariants[side].animate}
            exit={slideVariants[side].exit}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className={cn(
              "fixed top-0 bottom-0 z-50 w-[300px] max-w-[85vw] border-r border-border bg-card shadow-2xl flex flex-col",
              side === "left" ? "left-0" : "right-0 border-l border-r-0",
              className
            )}
          >
            {/* Close button */}
            <button
              onClick={() => onOpenChange(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors z-10"
              aria-label="Close navigation"
            >
              <X size={16} />
            </button>
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
