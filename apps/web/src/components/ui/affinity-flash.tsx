"use client"

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart } from 'lucide-react'
import { useEmotionalStore } from '@/store/emotional-store'

/**
 * AffinityFlashIndicator - Shows a flash animation when affinity increases
 *
 * Listens to the emotional store and displays a temporary "+X Affinity" notification
 * when affinity changes. The notification appears in the bottom-right corner with
 * a heart icon and fades out after 2 seconds.
 */
export function AffinityFlashIndicator() {
  const affinity = useEmotionalStore((state) => state.affinity)
  const [flash, setFlash] = React.useState<{ delta: number; show: boolean }>({ delta: 0, show: false })
  const prevAffinityRef = React.useRef(affinity)

  React.useEffect(() => {
    const prevAffinity = prevAffinityRef.current
    const delta = affinity - prevAffinity

    // Only show flash for positive changes > 0
    if (delta > 0) {
      setFlash({ delta, show: true })

      // Auto-hide after 2 seconds
      const timer = setTimeout(() => {
        setFlash((prev) => ({ ...prev, show: false }))
      }, 2000)

      return () => clearTimeout(timer)
    }

    prevAffinityRef.current = affinity
  }, [affinity])

  return (
    <AnimatePresence>
      {flash.show && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.8 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.8 }}
          transition={{ type: 'spring', bounce: 0.5, duration: 0.6 }}
          className="fixed bottom-6 right-6 z-[9999] pointer-events-none"
        >
          <div className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-gradient-to-r from-rose-500 to-pink-500 shadow-[0_10px_40px_rgba(244,63,94,0.5)] border border-white/20">
            <Heart size={20} className="text-white fill-white animate-pulse" />
            <span className="text-white font-black text-lg tracking-wide">
              +{flash.delta} Affinity
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
