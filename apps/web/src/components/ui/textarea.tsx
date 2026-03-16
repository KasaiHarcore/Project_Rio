"use client"

import React, { useEffect, useRef, useCallback } from "react"
import { cn } from "@/shared/lib/utils"

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Auto-grow the textarea to fit content */
  autoGrow?: boolean
  /** Maximum height in pixels before scrolling */
  maxHeight?: number
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, autoGrow = true, maxHeight = 200, onChange, value, ...props }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement | null>(null)

    const setRefs = useCallback(
      (node: HTMLTextAreaElement | null) => {
        internalRef.current = node
        if (typeof ref === "function") ref(node)
        else if (ref) (ref as React.MutableRefObject<HTMLTextAreaElement | null>).current = node
      },
      [ref]
    )

    const adjustHeight = useCallback(() => {
      const el = internalRef.current
      if (!el || !autoGrow) return
      el.style.height = "auto"
      el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`
      el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden"
    }, [autoGrow, maxHeight])

    useEffect(() => {
      adjustHeight()
    }, [value, adjustHeight])

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange?.(e)
      adjustHeight()
    }

    return (
      <textarea
        ref={setRefs}
        value={value}
        onChange={handleChange}
        rows={1}
        className={cn(
          "w-full resize-none bg-transparent text-sm font-bold tracking-wide outline-none text-foreground placeholder:text-muted-foreground/50 custom-scrollbar",
          className
        )}
        {...props}
      />
    )
  }
)

Textarea.displayName = "Textarea"
