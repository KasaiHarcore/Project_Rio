"use client"

import React, { useEffect, useState, useRef, useCallback } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import Script from 'next/script'
import { Play } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'
import { useUIStore } from '@/store/ui-store'

declare global {
  interface Window {
    spine: any;
    startAronaEngine: any;
    stopAronaEngine: any;
    setAronaCharacter: (id: string | null) => void;
    getAronaCharacter: () => string | null;
  }
}

// ==========================================
// ARONA PAGE : LEGACY ANIMATION PORT
// ==========================================
export default function AronaPage() {
    const [isStarted, setIsStarted] = useState(false);
    const { theme } = useTheme();
    const activeCharacterId = useUIStore((state) => state.activeCharacterId);
    const prevCharRef = useRef(activeCharacterId);
    
    // Sync forced character with the engine whenever the active character changes
    useEffect(() => {
        if (window.setAronaCharacter) {
            window.setAronaCharacter(activeCharacterId);
        }
    }, [activeCharacterId]);

    // If the character changes while the engine is running, restart it
    useEffect(() => {
        if (prevCharRef.current !== activeCharacterId && isStarted) {
            prevCharRef.current = activeCharacterId;
            if (window.setAronaCharacter) {
                window.setAronaCharacter(activeCharacterId);
            }
            if (window.startAronaEngine && window.spine) {
                console.log("[ARONA] Character changed, restarting engine...");
                window.startAronaEngine();
            }
        } else {
            prevCharRef.current = activeCharacterId;
        }
    }, [activeCharacterId, isStarted]);

    useEffect(() => {
        // Cleanup on unmount
        return () => {
            if (window.stopAronaEngine) {
                console.log("Unmounting Arona Engine...");
                window.stopAronaEngine();
            }
        };
    }, []);

    const handleStart = () => {
        setIsStarted(true);
        // Set the forced character before starting
        if (window.setAronaCharacter) {
            window.setAronaCharacter(activeCharacterId);
        }
        // Small delay to allow UI to update before heavy engine work
        setTimeout(() => {
             if (window.startAronaEngine && window.spine) {
                console.log("Triggering start...");
                window.startAronaEngine();
            }
        }, 100);
    };

    return (
        <DashboardLayout>
            <PageTransition className="relative w-full h-full flex flex-col overflow-hidden bg-black">
                {/* 
                    Legacy Script Container 
                    The script 'arona-main.js' expects specific IDs: 'canvas' and 'textbox'
                */}
                <div id="animation-container" className="relative w-full h-full">
                     <canvas id="canvas" className="w-full h-full block"></canvas>
                     {/* 
                        Use the legacy 'textbox' class to match arona-style.css 
                        This ensures the look is exact to the Template 
                     */}
                     <div 
                        id="textbox" 
                        className="textbox"
                        style={{ display: 'block' }}
                     >
                     </div>
                </div>

                {/* Click to Start Overlay */}
                {!isStarted && (
                    <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm transition-opacity duration-500">
                        <button 
                            onClick={handleStart}
                            className="group relative flex flex-col items-center gap-4 p-8 rounded-2xl hover:bg-white/5 transition-all"
                        >
                            <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 ring-1 ring-primary/50">
                                <Play className="w-8 h-8 text-primary fill-primary" />
                            </div>
                            <span className="text-white font-medium tracking-widest uppercase text-sm opacity-60 group-hover:opacity-100">
                                Click to Connect
                            </span>
                        </button>
                    </div>
                )}

                {/* Load Scripts Sequentially */}
                <Script 
                    src="/lib/spine-webgl.js" 
                    strategy="afterInteractive"
                    onLoad={() => {
                        console.log("Spine Loaded");
                    }}
                />
                <Script 
                    src="/js/arona-main.js" 
                    strategy="afterInteractive"
                    onLoad={() => {
                        console.log("Arona Engine Loaded");
                        // Wait for user interaction to start
                    }}
                />
                
                {/* Load CSS */}
                <link rel="stylesheet" href="/css/arona-style.css" />
            </PageTransition>
        </DashboardLayout>
    )
}
