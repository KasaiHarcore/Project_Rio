"use client"

import React, { useRef } from "react"
import { motion, useInView } from "framer-motion"
import { cn } from "@/lib/utils"

interface SparklineBarsProps {
    /** Array of data points (values) — typically 7 for week view */
    data: number[]
    /** Bar color (CSS value or var) */
    color?: string
    /** Height of the chart in px */
    height?: number
    /** Additional className */
    className?: string
}

export function SparklineBars({
    data,
    color = "var(--bento-bar-fill, #f43f5e)",
    height = 28,
    className,
}: SparklineBarsProps) {
    const ref = useRef<HTMLDivElement>(null)
    const isInView = useInView(ref, { once: true, margin: "-20px" })

    if (!data || data.length === 0) return null

    const max = Math.max(...data, 1) // avoid division by zero

    return (
        <div
            ref={ref}
            className={cn("flex items-end gap-[3px]", className)}
            style={{ height }}
            aria-hidden="true"
        >
            {data.map((value, i) => {
                const pct = (value / max) * 100
                // Opacity fades from dim (past) to full (present)
                const opacity = 0.25 + (i / (data.length - 1)) * 0.75

                return (
                    <motion.div
                        key={i}
                        className="flex-1 rounded-t-sm"
                        style={{
                            backgroundColor: color,
                            opacity,
                        }}
                        initial={{ height: 0 }}
                        animate={isInView ? { height: `${Math.max(pct, 8)}%` } : {}}
                        transition={{
                            duration: 0.5,
                            delay: 0.2 + i * 0.06,
                            ease: "easeOut",
                        }}
                    />
                )
            })}
        </div>
    )
}
