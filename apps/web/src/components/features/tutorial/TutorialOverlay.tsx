"use client"

import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'

interface Step {
    targetId: string // The ID of the element to highlight
    title: string
    content: string
    position: 'left' | 'right' | 'top' | 'bottom' | 'center'
    image: 'guide' | 'tip'
    action?: 'click_target' | null
}

const STEPS: Step[] = [
    {
        targetId: 'level-badge',
        title: 'Sensei Level',
        content: 'This represents your current knowledge level. Complete missions and study tasks to earn Experience Points!',
        position: 'right',
        image: 'tip'
    },
    {
        targetId: 'dashboard', // Sidebar Office button
        title: 'S.C.H.A.L.E Office',
        content: 'This is your main command center. You can check system status and active agents here.',
        position: 'right',
        image: 'guide'
    },
    {
        targetId: 'manual', // Sidebar Manual button
        title: 'System Manual',
        content: 'Lost? Access the documentation and guides here whenever you need help.',
        position: 'right',
        image: 'guide'
        // Removed action: 'click_target'
    },
    {
        targetId: 'settings', // Sidebar Settings button
        title: 'System Settings',
        content: 'Configure your preferences, API keys, and notification settings here.',
        position: 'right',
        image: 'tip'
    },
    {
        targetId: 'level-badge', // Focusing back on Sensei
        title: 'Good Luck, Sensei!',
        content: 'That concludes the briefing. Arona will be here to support your work. Let\'s do our best!',
        position: 'right',
        image: 'guide'
    }
]

export function TutorialOverlay() {
    const { isTutorialActive, tutorialStep, nextTutorialStep, endTutorial } = useUIStore()
    const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
    const currentStep = STEPS[tutorialStep]

    // Measure target position and scroll into view
    useEffect(() => {
        if (!isTutorialActive || !currentStep) return

        const updateRect = () => {
            const el = document.getElementById(currentStep.targetId)
            if (el) {
                setTargetRect(el.getBoundingClientRect())
            } else {
                // Fallback if element not found
                setTargetRect(null)
            }
        }

        // Trigger scroll if element exists
        const el = document.getElementById(currentStep.targetId)
        const sidebarContainer = document.getElementById('sidebar-scroll-container')

        if (el) {
            // If target is inside the sidebar scroll container, scroll ONLY that container
            if (sidebarContainer && sidebarContainer.contains(el)) {
                 const elRect = el.getBoundingClientRect()
                 const containerRect = sidebarContainer.getBoundingClientRect()
                 const currentScroll = sidebarContainer.scrollTop
                 
                 // Calculate desired scroll position (center element in container)
                 const relativeTop = elRect.top - containerRect.top
                 const targetScroll = currentScroll + relativeTop - (containerRect.height / 2) + (elRect.height / 2)

                 sidebarContainer.scrollTo({
                     top: targetScroll,
                     behavior: 'smooth'
                 })
            } else {
                 // Fallback for non-sidebar elements (like Level Badge if outside)
                 // Or if we don't mind page scrolling for header items
                 el.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }
        }

        // Poll for position updates during scroll (handling smooth scroll animation)
        updateRect()
        const intervalId = setInterval(updateRect, 20)
        const timeoutId = setTimeout(() => clearInterval(intervalId), 1000) // Stop polling after 1s

        // Listen for resize and scroll (capture phase for nested scrollers)
        window.addEventListener('resize', updateRect)
        window.addEventListener('scroll', updateRect, true) 

        return () => {
            window.removeEventListener('resize', updateRect)
            window.removeEventListener('scroll', updateRect, true)
            clearInterval(intervalId)
            clearTimeout(timeoutId)
        }
    }, [isTutorialActive, currentStep])

    const handleNext = () => {
        // If we are about to finish, check if we need to clean up listeners or just end
        if (tutorialStep >= STEPS.length - 1) {
            endTutorial()
        } else {
            nextTutorialStep()
        }
    }

    // Handle interactive steps (click detection)
    useEffect(() => {
        if (!isTutorialActive || !currentStep) return
        
        if (currentStep.action === 'click_target') {
            const el = document.getElementById(currentStep.targetId)
            if (!el) return

            const onTargetClick = () => {
                // Give a small delay to allow animation or navigation to start
                setTimeout(() => {
                    handleNext()
                }, 300)
            }

            el.addEventListener('click', onTargetClick)
            return () => el.removeEventListener('click', onTargetClick)
        }
    }, [isTutorialActive, currentStep, tutorialStep]) // Re-run when step changes

    if (!isTutorialActive || !currentStep) return null

    return (
        <AnimatePresence>
            <motion.div 
                key="overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] overflow-hidden pointer-events-none" // Main container pointer-events-none
            >
                {/* Visual Overlay with Spotlights */}
                <div className="absolute inset-0 transition-all duration-500">
                    <svg className="absolute inset-0 w-full h-full pointer-events-none"> 
                        <defs>
                            <mask id="spotlight-mask">
                                <rect width="100%" height="100%" fill="white" />
                                {targetRect && (
                                    <rect 
                                        x={targetRect.left - 10} 
                                        y={targetRect.top - 10} 
                                        width={targetRect.width + 20} 
                                        height={targetRect.height + 20} 
                                        rx="12"
                                        fill="black" 
                                    />
                                )}
                            </mask>
                        </defs>
                        {/* Light Gray Outside (as requested) */}
                        <rect width="100%" height="100%" fill="rgba(200, 200, 200, 0.4)" mask="url(#spotlight-mask)" />
                    </svg>
                </div>

                {/* Highlight Box Ring (Animation) */}
                {targetRect && (
                    <motion.div 
                        layoutId="highlight-box"
                        className="absolute border-2 border-[#1289F4] rounded-xl shadow-[0_0_50px_rgba(18,137,244,0.3)] pointer-events-none"
                        style={{
                            left: targetRect.left - 10,
                            top: targetRect.top - 10,
                            width: targetRect.width + 20,
                            height: targetRect.height + 20,
                        }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                )}

                {/* Content Card & Arona */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    {/* Positioning logic based on target */}
                    <motion.div 
                        key={currentStep.title} // Re-render on step change for pop effect
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                         className={cn(
                            "pointer-events-auto absolute flex items-end gap-0",
                            // Dynamic positioning classes based on step preference
                            // For simplicity in this v1, checking 'position' prop
                        )}
                        style={{
                            // Robust positioning logic
                            position: 'absolute',
                            ...(targetRect ? {
                                ...(currentStep.position === 'right' ? {
                                    left: targetRect.right + 20,
                                    top: targetRect.top + (targetRect.height / 2) - 50, // Center-ish relative to target
                                } : {}),
                                ...(currentStep.position === 'bottom' ? {
                                    top: targetRect.bottom + 20,
                                    left: targetRect.left + (targetRect.width / 2) - 100, // Center horizontal
                                } : {}),
                                // Default center if no pos match (should cover 'center' case)
                                ...(currentStep.position === 'center' ? {
                                    top: '50%',
                                    left: '50%',
                                    transform: 'translate(-50%, -50%)'
                                } : {})
                            } : {
                                // Fallback if no target found
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)'
                            })
                        }}
                    >
                         {/* Arona Image */}
                         <div className="relative z-20 -mr-12 mb-[-20px]">
                            <img 
                                src={`/images/arona_${currentStep.image || 'guide'}.png`} 
                                alt="Arona" 
                                className="w-48 object-contain drop-shadow-xl hover:scale-105 transition-transform"
                            />
                         </div>

                         {/* Dialogue Box */}
                         <div className="bg-white rounded-t-[30px] rounded-br-[30px] rounded-bl-sm p-6 shadow-2xl max-w-md border-2 border-[#1289F4] relative z-10 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]">
                             <div className="flex justify-between items-start mb-2">
                                 <h3 className="text-xl font-black text-[#1289F4] tracking-wider uppercase">
                                     {currentStep.title}
                                 </h3>
                                 <div className="text-xs font-bold text-slate-300 bg-slate-50 px-2 py-1 rounded">
                                     Step {tutorialStep + 1} / {STEPS.length}
                                 </div>
                             </div>
                             
                             <p className="text-slate-600 font-medium leading-relaxed mb-6 text-sm">
                                 {currentStep.content}
                             </p>

                             <div className="flex justify-end gap-2">
                                 {/* Interactive Step? */}
                                 {currentStep.action === 'click_target' ? (
                                     <div className="text-xs font-bold text-[#1289F4] animate-pulse flex items-center">
                                         Click highlight to continue...
                                     </div>
                                 ) : (
                                     <button 
                                        onClick={handleNext}
                                        className="bg-[#1289F4] hover:bg-blue-600 text-white px-6 py-2 rounded-full font-bold text-sm shadow-md transition-all hover:shadow-lg active:scale-95 flex items-center gap-2"
                                     >
                                        {tutorialStep === STEPS.length - 1 ? "Let's Go!" : "Next"}
                                        <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                                     </button>
                                 )}
                             </div>

                             {/* Little triangle tail */}
                             <div className="absolute -left-3 bottom-8 w-0 h-0 border-t-[10px] border-t-transparent border-r-[15px] border-r-[#1289F4] border-b-[10px] border-b-transparent transform rotate-12" />
                         </div>
                    </motion.div>
                </div>

            </motion.div>
        </AnimatePresence>
    )
}
