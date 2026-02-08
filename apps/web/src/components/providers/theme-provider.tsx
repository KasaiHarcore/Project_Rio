"use client"

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react"

type Theme = "dark" | "light"

interface ThemeProviderProps {
  children: React.ReactNode
  defaultTheme?: Theme
}

interface ThemeProviderState {
  theme: Theme
  /** Set theme (used by auto-cycle). Does NOT disable auto mode. */
  setTheme: (theme: Theme) => void
  /** Set theme manually (user action). Disables auto-cycle for this session until 7h expire or page reload. */
  setThemeManual: (theme: Theme) => void
  /** Whether the auto day/night cycle is active */
  isAutoMode: boolean
}

const OVERRIDE_KEY = "theme-override-ts"
const OVERRIDE_DURATION_MS = 7 * 60 * 60 * 1000 // 7 hours

const initialState: ThemeProviderState = {
  theme: "light",
  setTheme: () => null,
  setThemeManual: () => null,
  isAutoMode: true,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
  children,
  defaultTheme = "light",
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme)
  const [isMounted, setIsMounted] = useState(false)
  const [isAutoMode, setIsAutoMode] = useState(true)
  const autoModeRef = useRef(true)

  // Calculate theme based on time
  const getThemeFromTime = (): Theme => {
    const hours = new Date().getHours()
    // Night is 18:00 (6 PM) to 6:00 (6 AM)
    const isNight = hours >= 18 || hours < 6
    return isNight ? "dark" : "light"
  }

  const applyTheme = useCallback((newTheme: Theme) => {
    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    root.classList.add(newTheme)
    setTheme(newTheme)
  }, [])

  // Check if a previous manual override is still valid (< 7 hours old)
  const checkExistingOverride = useCallback((): { active: boolean; theme?: Theme } => {
    try {
      const stored = sessionStorage.getItem(OVERRIDE_KEY)
      if (!stored) return { active: false }
      
      const data = JSON.parse(stored) as { ts: number; theme: Theme }
      const elapsed = Date.now() - data.ts
      
      if (elapsed < OVERRIDE_DURATION_MS) {
        return { active: true, theme: data.theme }
      }
      // Expired — clear it
      sessionStorage.removeItem(OVERRIDE_KEY)
      return { active: false }
    } catch {
      return { active: false }
    }
  }, [])

  useEffect(() => {
    setIsMounted(true)

    // Check for a still-valid manual override from this session
    const override = checkExistingOverride()
    
    if (override.active && override.theme) {
      // Restore user's manual choice
      applyTheme(override.theme)
      setIsAutoMode(false)
      autoModeRef.current = false
    } else {
      // Fresh session or override expired → use time-based auto
      const initialTheme = getThemeFromTime()
      applyTheme(initialTheme)
      setIsAutoMode(true)
      autoModeRef.current = true
    }

    // Check every minute: auto-switch if in auto mode, or expire the override
    const interval = setInterval(() => {
      // Check if override has expired
      if (!autoModeRef.current) {
        const overrideCheck = (() => {
          try {
            const stored = sessionStorage.getItem(OVERRIDE_KEY)
            if (!stored) return true // no override stored, re-enable
            const data = JSON.parse(stored) as { ts: number; theme: Theme }
            return (Date.now() - data.ts) >= OVERRIDE_DURATION_MS
          } catch {
            return true
          }
        })()

        if (overrideCheck) {
          // Override expired → re-enable auto mode
          sessionStorage.removeItem(OVERRIDE_KEY)
          autoModeRef.current = true
          setIsAutoMode(true)
        }
      }

      // Only auto-switch when in auto mode
      if (autoModeRef.current) {
        const newTheme = getThemeFromTime()
        setTheme((prev) => {
          if (prev !== newTheme) {
            const root = window.document.documentElement
            root.classList.remove("light", "dark")
            root.classList.add(newTheme)
            return newTheme
          }
          return prev
        })
      }
    }, 60000) 

    return () => clearInterval(interval)
  }, [applyTheme, checkExistingOverride])

  const value: ThemeProviderState = {
    theme,
    isAutoMode,
    // Regular setTheme — used by auto-cycle syncing, doesn't disable auto
    setTheme: (newTheme: Theme) => {
      applyTheme(newTheme)
    },
    // Manual setTheme — user clicked a character, disables auto-cycle
    setThemeManual: (newTheme: Theme) => {
      applyTheme(newTheme)
      setIsAutoMode(false)
      autoModeRef.current = false
      try {
        sessionStorage.setItem(OVERRIDE_KEY, JSON.stringify({ ts: Date.now(), theme: newTheme }))
      } catch { /* sessionStorage unavailable */ }
    },
  }

  // Prevent flash of incorrect theme (SSR mismatch)
  if (!isMounted) {
    return <>{children}</>
  }

  return (
    <ThemeProviderContext.Provider value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)

  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider")

  return context
}
