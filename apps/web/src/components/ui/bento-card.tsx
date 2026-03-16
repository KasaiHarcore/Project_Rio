"use client"

import React, { useRef } from 'react'
import { motion, useMotionTemplate, useMotionValue } from 'framer-motion'
import { cn } from '@/shared/lib/utils'

interface BentoCardProps {
  children: React.ReactNode
  className?: string
  noHover?: boolean
}

export function BentoCard({ children, className, noHover = false }: BentoCardProps) {
  const ref = useRef<HTMLDivElement>(null)

  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    if (noHover) return
    const { left, top } = currentTarget.getBoundingClientRect()
    mouseX.set(clientX - left)
    mouseY.set(clientY - top)
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={noHover ? {} : { scale: 1.02, y: -2 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className={cn(
        "group relative rounded-xl border p-5 overflow-hidden transition-colors duration-500",
        "backdrop-blur-md",
        "bg-[var(--bento-bg)] border-[var(--bento-edge-border,var(--bento-border))] hover:bg-[var(--bento-hover-bg)]",
        className
      )}
      style={{
        boxShadow: 'var(--bento-inset-highlight, inset 0 1px 0 rgba(255,255,255,0.05))',
      }}
    >
      {/* Glare Effect Layer */}
      {!noHover && (
        <motion.div
          className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100"
          style={{
            background: useMotionTemplate`
              radial-gradient(
                650px circle at ${mouseX}px ${mouseY}px,
                var(--bento-glare),
                transparent 80%
              )
            `,
          }}
        />
      )}

      {/* Top-edge highlight line */}
      <div
        className="pointer-events-none absolute top-0 left-0 right-0 h-px z-20"
        style={{ background: 'var(--bento-top-line, linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%))' }}
      />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  )
}
