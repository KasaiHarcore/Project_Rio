import React, { useEffect } from 'react'
import { Sidebar } from './sidebar'
import { MobileNav } from './mobile-nav'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'
import { TutorialOverlay } from '@/components/features/tutorial/TutorialOverlay'
import { PageTransition } from './page-transition'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { splashSeen, startTutorial, isTutorialActive, tutorialCompleted } = useUIStore()
  useKeyboardShortcuts()
  
  // Trigger tutorial after splash screen if not already completed
  useEffect(() => {
    if (splashSeen && !isTutorialActive && !tutorialCompleted) {
      const timer = setTimeout(() => startTutorial(), 1000)
      return () => clearTimeout(timer)
    }
  }, [splashSeen, isTutorialActive, tutorialCompleted, startTutorial])
  
  return (
    <div className={cn(
        "flex h-screen font-sans text-foreground overflow-hidden relative transition-colors duration-1000",
        "bg-background selection:bg-[var(--selection-bg)]"
    )}>
        {/* Background - Grid + Ambient Orbs (themed via CSS vars) */}
        <div className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-1000">
            {/* Grid Pattern */}
            <div
                className="absolute inset-0 bg-[size:4rem_4rem] transition-colors duration-1000 bg-[linear-gradient(to_right,var(--grid-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--grid-line)_1px,transparent_1px)]"
                style={{maskImage: 'radial-gradient(ellipse 60% 50% at 50% 0%, #000 70%, transparent 100%)'}}
            ></div>

            {/* Ambient Orbs */}
            <div className="absolute top-[-20%] left-[-10%] h-[50%] w-[50%] animate-pulse rounded-full mix-blend-multiply blur-[120px] transition-colors duration-1000 bg-[var(--glow-ambient)]"></div>
            <div className="absolute right-[-10%] bottom-[-20%] h-[50%] w-[50%] rounded-full mix-blend-multiply blur-[120px] transition-colors duration-1000 bg-[var(--glow-ambient-secondary)]"></div>
        </div>

        {/* Sidebar (desktop) */}
        <Sidebar className="flex-shrink-0" />

        {/* Main Content Area */}
        <main id="main-content" className="flex-1 relative z-10 overflow-hidden flex flex-col">
            {/* Mobile Nav (shows on <lg) */}
            <MobileNav />
            <PageTransition className="flex-1 flex flex-col overflow-hidden">
              {children}
            </PageTransition>
        </main>
        
        {/* Overlays */}
        <TutorialOverlay />
    </div>
  )
}
