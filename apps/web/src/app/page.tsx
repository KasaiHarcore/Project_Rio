"use client"

import React, { useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { AnimatePresence, motion } from "framer-motion"
import { useUIStore } from '@/shared/store/ui-store'
import { useShallow } from 'zustand/react/shallow'

// Lazy-load heavy dashboard views — only one is visible at a time
const MissionBoard = dynamic(
  () => import("@/features/dashboard/components/MissionBoard").then((m) => m.MissionBoard),
)
const MissionControl = dynamic(
  () => import("@/features/mission/components/MissionControl").then((m) => m.MissionControl),
)
const SplashScreen = dynamic(
  () => import("@/components/layout/splash-screen").then((m) => m.SplashScreen),
  { ssr: false },
)

export default function Page() {
  const { splashSeen, setSplashSeen, hydrateFromStorage, viewMode, activeMissionId } = useUIStore(
    useShallow((state) => ({
      splashSeen: state.splashSeen,
      setSplashSeen: state.setSplashSeen,
      hydrateFromStorage: state.hydrateFromStorage,
      viewMode: state.viewMode,
      activeMissionId: state.activeMissionId,
    }))
  )

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

