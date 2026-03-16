"use client"

import React, { useRef } from "react"
import { motion, useInView } from "framer-motion"
import { cn } from "@/shared/lib/utils"

interface SparklineChartProps {
  /** Array of data points (values) */
  data: number[]
  /** Width of the chart in px */
  width?: number
  /** Height of the chart in px */
  height?: number
  /** Stroke color — supports CSS vars via style */
  color?: string
  /** Whether to show the gradient fill underneath */
  fill?: boolean
  /** Additional className */
  className?: string
}

export function SparklineChart({
  data,
  width = 120,
  height = 32,
  color = "currentColor",
  fill = true,
  className,
}: SparklineChartProps) {
  const ref = useRef<SVGSVGElement>(null)
  const isInView = useInView(ref, { once: true, margin: "-20px" })

  if (!data || data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  // Padding to avoid clipping at edges
  const padX = 2
  const padY = 4
  const innerW = width - padX * 2
  const innerH = height - padY * 2

  const points = data.map((val, i) => {
    const x = padX + (i / (data.length - 1)) * innerW
    const y = padY + innerH - ((val - min) / range) * innerH
    return `${x},${y}`
  })

  const pathD = points.join(" ")

  // For the fill area, close the path along the bottom
  const fillPoints = [
    ...points,
    `${padX + innerW},${height}`,
    `${padX},${height}`,
  ].join(" ")

  const gradientId = `sparkline-grad-${Math.random().toString(36).slice(2, 8)}`

  return (
    <svg
      ref={ref}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={cn("overflow-visible", className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Gradient fill area */}
      {fill && (
        <motion.polygon
          points={fillPoints}
          fill={`url(#${gradientId})`}
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.4 }}
        />
      )}

      {/* Line */}
      <motion.polyline
        points={pathD}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={isInView ? { pathLength: 1, opacity: 1 } : {}}
        transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
      />

      {/* End dot */}
      <motion.circle
        cx={padX + innerW}
        cy={padY + innerH - ((data[data.length - 1] - min) / range) * innerH}
        r={3}
        fill={color}
        initial={{ scale: 0, opacity: 0 }}
        animate={isInView ? { scale: 1, opacity: 1 } : {}}
        transition={{ duration: 0.3, delay: 1.2 }}
      />
    </svg>
  )
}
