"use client"

import React, { useEffect, useRef, useState } from "react"
import { useInView, useMotionValue, useSpring } from "framer-motion"

interface AnimatedCounterProps {
  /** Target value to count to */
  value: number
  /** Duration in seconds */
  duration?: number
  /** Decimal places to display */
  decimals?: number
  /** Prefix (e.g., "$") */
  prefix?: string
  /** Suffix (e.g., "K", "%") */
  suffix?: string
  /** Additional className for the number */
  className?: string
  /** Suffix className */
  suffixClassName?: string
}

export function AnimatedCounter({
  value,
  duration = 1.5,
  decimals = 0,
  prefix = "",
  suffix = "",
  className = "",
  suffixClassName = "",
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, margin: "-40px" })
  const motionValue = useMotionValue(0)
  const springValue = useSpring(motionValue, {
    stiffness: 80,
    damping: 30,
    duration: duration * 1000,
  })
  const [display, setDisplay] = useState("0")

  useEffect(() => {
    if (isInView) {
      motionValue.set(value)
    }
  }, [isInView, value, motionValue])

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      const formatted =
        decimals > 0
          ? latest.toFixed(decimals)
          : Math.round(latest).toString()

      // Pad with leading zero for single-digit values when target is >= 10
      if (value >= 10 && Math.round(latest) < 10 && decimals === 0) {
        setDisplay("0" + formatted)
      } else {
        setDisplay(formatted)
      }
    })
    return unsubscribe
  }, [springValue, decimals, value])

  return (
    <span ref={ref} className={className}>
      {prefix}
      {display}
      {suffix && (
        <span className={suffixClassName}>{suffix}</span>
      )}
    </span>
  )
}
