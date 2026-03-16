"use client"

import React from "react"
import { cn } from "@/shared/lib/utils"

interface DeltaBadgeProps {
    /** The delta value, e.g. 22.4 or -3 */
    value: number
    /** Unit suffix, e.g. "%" or "" */
    suffix?: string
    /** Optional context label, e.g. "vs yesterday" */
    context?: string
    /** Additional className */
    className?: string
}

export function DeltaBadge({ value, suffix = "", context, className }: DeltaBadgeProps) {
    const direction = value > 0 ? "up" : value < 0 ? "down" : "neutral"
    const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "→"
    const displayValue = Math.abs(value)

    return (
        <div className={cn("flex items-center gap-2", className)}>
            <span
                className={cn(
                    "inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full",
                    direction === "up" && "bg-[var(--delta-up-bg)] text-[var(--delta-up-text)]",
                    direction === "down" && "bg-[var(--delta-down-bg)] text-[var(--delta-down-text)]",
                    direction === "neutral" && "bg-[var(--delta-neutral-bg)] text-[var(--delta-neutral-text)]"
                )}
            >
                {arrow} {displayValue}{suffix}
            </span>
            {context && (
                <span className="text-[11px] text-muted-foreground">{context}</span>
            )}
        </div>
    )
}
