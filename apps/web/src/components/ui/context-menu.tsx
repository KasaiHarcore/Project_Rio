"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { createPortal } from "react-dom"

// ─── Types ─────────────────────────────────────────────────────
export interface ContextMenuItem {
  id: string
  label: string
  icon?: React.ReactNode
  shortcut?: string
  danger?: boolean
  disabled?: boolean
  action: () => void
}

export interface ContextMenuDivider {
  type: "divider"
}

export type ContextMenuEntry = ContextMenuItem | ContextMenuDivider

interface ContextMenuProps {
  /** The trigger element — children are wrapped with onContextMenu */
  children: React.ReactNode
  /** Menu items to display */
  items: ContextMenuEntry[]
  /** Additional className for the trigger wrapper */
  className?: string
  /** Disable the context menu */
  disabled?: boolean
}

// ─── Helper ────────────────────────────────────────────────────
function isDivider(entry: ContextMenuEntry): entry is ContextMenuDivider {
  return "type" in entry && entry.type === "divider"
}

// ─── Component ─────────────────────────────────────────────────
export function ContextMenu({ children, items, className, disabled }: ContextMenuProps) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const menuRef = useRef<HTMLDivElement>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const close = useCallback(() => {
    setOpen(false)
    setSelectedIndex(-1)
  }, [])

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      if (disabled) return
      e.preventDefault()
      e.stopPropagation()

      // Calculate position, ensuring the menu stays within viewport
      const x = Math.min(e.clientX, window.innerWidth - 220)
      const y = Math.min(e.clientY, window.innerHeight - items.length * 40 - 20)

      setPosition({ x, y })
      setOpen(true)
      setSelectedIndex(-1)
    },
    [disabled, items.length]
  )

  // Close on outside click or scroll
  useEffect(() => {
    if (!open) return
    const handleClick = () => close()
    const handleScroll = () => close()
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close()
    }
    document.addEventListener("mousedown", handleClick)
    document.addEventListener("scroll", handleScroll, true)
    document.addEventListener("keydown", handleKey)
    return () => {
      document.removeEventListener("mousedown", handleClick)
      document.removeEventListener("scroll", handleScroll, true)
      document.removeEventListener("keydown", handleKey)
    }
  }, [open, close])

  // Keyboard navigation within menu
  const actionItems = items.filter((item): item is ContextMenuItem => !isDivider(item) && !item.disabled)

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((prev) => Math.min(prev + 1, actionItems.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((prev) => Math.max(prev - 1, 0))
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (selectedIndex >= 0) {
        actionItems[selectedIndex]?.action()
        close()
      }
    }
  }

  return (
    <>
      <div onContextMenu={handleContextMenu} className={className}>
        {children}
      </div>

      {mounted &&
        createPortal(
          <AnimatePresence>
            {open && (
              <>
                {/* Invisible overlay to capture clicks */}
                <div className="fixed inset-0 z-[200]" onMouseDown={close} />

                <motion.div
                  ref={menuRef}
                  initial={{ opacity: 0, scale: 0.92, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.92, y: -4 }}
                  transition={{ duration: 0.12, ease: [0.32, 0.72, 0, 1] }}
                  onKeyDown={handleMenuKeyDown}
                  tabIndex={0}
                  className="fixed z-[201] min-w-[200px] overflow-hidden rounded-xl border border-border bg-card p-1.5 shadow-xl backdrop-blur-xl"
                  style={{ left: position.x, top: position.y }}
                >
                  {items.map((entry, idx) => {
                    if (isDivider(entry)) {
                      return (
                        <div
                          key={`divider-${idx}`}
                          className="my-1 h-px bg-border"
                        />
                      )
                    }

                    const actionIdx = actionItems.indexOf(entry)
                    const isSelected = actionIdx === selectedIndex

                    return (
                      <button
                        key={entry.id}
                        disabled={entry.disabled}
                        onMouseEnter={() => setSelectedIndex(actionIdx)}
                        onClick={(e) => {
                          e.stopPropagation()
                          entry.action()
                          close()
                        }}
                        className={cn(
                          "w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                          entry.disabled && "opacity-40 cursor-not-allowed",
                          entry.danger
                            ? isSelected
                              ? "bg-destructive/10 text-destructive"
                              : "text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                            : isSelected
                              ? "bg-primary/10 text-foreground"
                              : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {entry.icon && (
                          <span className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                            {entry.icon}
                          </span>
                        )}
                        <span className="flex-1 font-medium">{entry.label}</span>
                        {entry.shortcut && (
                          <span className="text-[10px] font-mono text-muted-foreground/50">
                            {entry.shortcut}
                          </span>
                        )}
                      </button>
                    )
                  })}
                </motion.div>
              </>
            )}
          </AnimatePresence>,
          document.body
        )}
    </>
  )
}
