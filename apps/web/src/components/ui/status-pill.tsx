"use client"

import React from "react"
import { cn } from "@/lib/utils"

interface StatusPillProps {
    /** "live" = green pulsing dot, "idle" = gray static dot */
    variant: "live" | "idle"
    /** Label text, e.g. "Active" / "Idle" / "3 running" */
    label: string
    /** Additional className */
    className?: string
}

export function StatusPill({ variant, label, className }: StatusPillProps) {
    const isLive = variant === "live"

    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full select-none",
                isLive
                    ? "bg-[var(--status-live-bg)] text-[var(--status-live-text)]"
                    : "bg-[var(--status-idle-bg)] text-[var(--status-idle-text)]",
                className
            )}
        >
            <span
                className={cn(
                    "w-[5px] h-[5px] rounded-full flex-shrink-0",
                    isLive
                        ? "bg-[var(--status-live-dot)] shadow-[0_0_6px_var(--status-live-dot)] animate-pulse"
                        : "bg-[var(--status-idle-text)]"
                )}
            />
            {label}
        </span>
    )
}
