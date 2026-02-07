"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { MissionBoard } from "@/components/features/dashboard/MissionBoard"
import { MissionControl } from "@/components/features/mission/MissionControl"
import { SplashScreen } from "@/components/layout/splash-screen"
import { AnimatePresence, motion } from "framer-motion"
import { useUIStore } from '@/store/ui-store'

export default function Page() {
  const splashSeen = useUIStore((state) => state.splashSeen)
  const setSplashSeen = useUIStore((state) => state.setSplashSeen)
  const [showSplash, setShowSplash] = useState(!splashSeen)
  const viewMode = useUIStore((state) => state.viewMode)

  const handleSplashComplete = () => {
    setShowSplash(false)
    setSplashSeen(true)
  }

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
              <AnimatePresence mode="popLayout" initial={false}>
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
                          <MissionControl />
                      </motion.div>
                  )}
              </AnimatePresence>
           </PageTransition>
        </DashboardLayout>
      )}
    </>
  )
}

