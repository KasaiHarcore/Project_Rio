"use client"

import React, { createContext, useContext, useEffect, useState } from "react"

type Theme = "dark" | "light"

interface ThemeProviderProps {
  children: React.ReactNode
  defaultTheme?: Theme
}

interface ThemeProviderState {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const initialState: ThemeProviderState = {
  theme: "light",
  setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
  children,
  defaultTheme = "light",
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme)
  const [isMounted, setIsMounted] = useState(false)

  // Calculate theme based on time
  const getThemeFromTime = (): Theme => {
    const hours = new Date().getHours()
    // Night is 18:00 (6 PM) to 6:00 (6 AM)
    const isNight = hours >= 18 || hours < 6
    return isNight ? "dark" : "light"
  }

  useEffect(() => {
    setIsMounted(true)
    const initialTheme = getThemeFromTime()
    setTheme(initialTheme)

    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    root.classList.add(initialTheme)

    // Optional: Check every minute to switch automatically
    const interval = setInterval(() => {
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
    }, 60000) 

    return () => clearInterval(interval)
  }, [])

  const value = {
    theme,
    setTheme: (newTheme: Theme) => {
      const root = window.document.documentElement
      root.classList.remove("light", "dark")
      root.classList.add(newTheme)
      setTheme(newTheme)
    },
  }

  // Prevent flash of incorrect theme (SSR mismatch)
  // Though typically we'd accept the flash for better performance, 
  // here we want to ensure the class is correct.
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
