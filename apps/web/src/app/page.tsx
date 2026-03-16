"use client"

import React, { useEffect, useRef, useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { MissionBoard } from "@/features/dashboard/components/MissionBoard"
import { MissionControl } from "@/features/mission/components/MissionControl"
import { SplashScreen } from "@/components/layout/splash-screen"
import { AnimatePresence, motion } from "framer-motion"
import { useUIStore } from '@/shared/store/ui-store'

export default function Page() {
  const splashSeen = useUIStore((state) => state.splashSeen)
  const setSplashSeen = useUIStore((state) => state.setSplashSeen)
  const hydrateFromStorage = useUIStore((state) => state.hydrateFromStorage)
  const viewMode = useUIStore((state) => state.viewMode)
  const activeMissionId = useUIStore((state) => state.activeMissionId)

  // Hydrate persisted state from localStorage after mount (avoids SSR mismatch)
  const hydrated = useRef(false)
  useEffect(() => {
    if (!hydrated.current) {
      hydrateFromStorage()
      hydrated.current = true
    }
  }, [hydrateFromStorage])

  // null = pending hydration, true = show splash, false = skip
  const [showSplash, setShowSplash] = useState<boolean | null>(null)

  // Once hydration sets splashSeen, decide whether to show the splash
  useEffect(() => {
    if (!hydrated.current) return
    // splashSeen===true means "already seen / skip" → no splash
    // splashSeen===false means "should play" → show splash
    setShowSplash(!splashSeen)
  }, [splashSeen])

  const handleSplashComplete = () => {
    setShowSplash(false)
    setSplashSeen(true)
  }

  // Still deciding — render nothing to avoid a flash
  if (showSplash === null) return null

  return (
    <>
      <AnimatePresence>
        {showSplash && (
          <SplashScreen onComplete={handleSplashComplete} />
        )}
      </AnimatePresence>
      
      {!showSplash && (
        <DashboardLayout>
           <PageTransition className="flex flex-1 overflow-hidden relative">
              <AnimatePresence mode="popLayout">
                  {viewMode === 'dashboard' ? (
                      <motion.div 
                        key="dashboard"
                        initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
                        animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
                        transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
                        className="flex-1 overflow-hidden flex absolute inset-0 z-10"
                      >
                          <MissionBoard />
                      </motion.div>
                  ) : (
                      <motion.div 
                        key="mission-control"
                        initial={{ opacity: 0, scale: 1.1, filter: 'blur(10px)' }}
                        animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, scale: 1.1, filter: 'blur(10px)' }}
                        transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
                        className="flex-1 overflow-hidden flex h-full absolute inset-0 z-20 bg-white/50 backdrop-blur-xl"
                      >
                          <MissionControl threadId={activeMissionId} />
                      </motion.div>
                  )}
              </AnimatePresence>
           </PageTransition>
        </DashboardLayout>
      )}
    </>
  )
}

