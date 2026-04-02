"use client"

import React from "react"
import { cn } from "@/shared/lib/utils"

interface KbdProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode
}

export function Kbd({ className, children, ...props }: KbdProps) {
  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded border text-[10px] font-mono font-bold select-none",
        "bg-muted/80 border-border text-muted-foreground shadow-[0_1px_0_1px] shadow-border/50",
        className
      )}
      {...props}
    >
      {children}
    </kbd>
  )
}
