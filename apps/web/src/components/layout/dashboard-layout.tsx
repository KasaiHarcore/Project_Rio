import React, { useEffect } from 'react'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'
import { TutorialOverlay } from '@/components/features/tutorial/TutorialOverlay'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { activeCharacterId, splashSeen, startTutorial, isTutorialActive } = useUIStore()
  
  // Trigger tutorial just after splash screen (simulated logic)
  useEffect(() => {
    // Only run if splash finished and tutorial is NOT inactive (to prevent restarts)
    if (splashSeen && !isTutorialActive) {
        // In a real app, check localStorage.getItem('tutorial_completed')
        const hasDoneTutorial = false // DEV: FORCE TUTORIAL ALWAYS
        if (!hasDoneTutorial) {
             const timer = setTimeout(() => startTutorial(), 1000)
             return () => clearTimeout(timer) 
        }
    }
  }, [splashSeen]) // Ensure we don't re-run on other state changes

  // Theme logic
  const isPlana = activeCharacterId === 'plana'
  
  return (
    <div className={cn(
        "flex h-screen font-sans text-foreground overflow-hidden relative transition-colors duration-1000",
        isPlana ? "bg-[#1a1625] selection:bg-rose-500/30" : "bg-background selection:bg-primary/30"
    )}>
        {/* Background - Exact match from chat.html */}
        <div className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-1000">
            {/* Grid Pattern */}
            <div className={cn(
                "absolute inset-0 bg-[size:4rem_4rem] transition-colors duration-1000",
                isPlana 
                    ? "bg-[linear-gradient(to_right,#ef44441a_1px,transparent_1px),linear-gradient(to_bottom,#ef44441a_1px,transparent_1px)]"
                    : "bg-[linear-gradient(to_right,color-mix(in_srgb,var(--primary),transparent_90%)_1px,transparent_1px),linear-gradient(to_bottom,color-mix(in_srgb,var(--primary),transparent_90%)_1px,transparent_1px)]"
            )} style={{maskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, #000 70%, transparent 100%)'}}></div>

            {/* Ambient Orbs */}
            <div className={cn(
                "absolute top-[-20%] left-[-10%] h-[50%] w-[50%] animate-pulse rounded-full mix-blend-multiply blur-[120px] transition-colors duration-1000",
                isPlana ? "bg-rose-900/40" : "bg-primary/20"
            )}></div>
            <div className={cn(
                "absolute right-[-10%] bottom-[-20%] h-[50%] w-[50%] rounded-full mix-blend-multiply blur-[120px] transition-colors duration-1000",
                isPlana ? "bg-purple-900/40" : "bg-primary/10"
            )}></div>
        </div>

        {/* Sidebar */}
        <Sidebar className="flex-shrink-0" />

        {/* Main Content Area */}
        <main className="flex-1 relative z-10 overflow-hidden flex flex-col">
            {children}
        </main>
        
        {/* Overlays */}
        <TutorialOverlay />
    </div>
  )
}
