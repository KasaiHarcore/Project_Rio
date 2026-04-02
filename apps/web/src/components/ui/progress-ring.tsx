"use client"

import React, { useRef } from "react"
import { motion, useInView } from "framer-motion"
import { cn } from "@/shared/lib/utils"

interface ProgressRingProps {
  /** Progress value (0-100) */
  value: number
  /** Size of the ring in px */
  size?: number
  /** Stroke width */
  strokeWidth?: number
  /** Track color */
  trackColor?: string
  /** Progress color */
  progressColor?: string
  /** Whether to show the value label inside */
  showLabel?: boolean
  /** Label className */
  labelClassName?: string
  /** Additional className */
  className?: string
  /** Children rendered inside the ring */
  children?: React.ReactNode
}

export function ProgressRing({
  value,
  size = 80,
  strokeWidth = 6,
  trackColor = "var(--bento-bar-track, rgba(100,116,139,0.2))",
  progressColor = "var(--progress-ring-color, #10b981)",
  showLabel = false,
  labelClassName,
  className,
  children,
}: ProgressRingProps) {
  const ref = useRef<SVGSVGElement>(null)
  const isInView = useInView(ref, { once: true, margin: "-20px" })

  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(Math.max(value, 0), 100)
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg
        ref={ref}
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        aria-hidden="true"
      >
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        {/* Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={progressColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={isInView ? { strokeDashoffset: offset } : {}}
          transition={{ duration: 1.5, ease: [0.32, 0.72, 0, 1], delay: 0.1 }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {children ?? (
          showLabel && (
            <span className={cn("text-sm font-black", labelClassName)}>
              {progress}%
            </span>
          )
        )}
      </div>
    </div>
  )
}
