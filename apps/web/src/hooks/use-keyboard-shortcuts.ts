"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useUIStore } from "@/store/ui-store"

/**
 * Global keyboard shortcuts for the application.
 *
 * Shortcuts:
 *   /       → Focus the chat input (if visible)
 *   Escape  → Close overlays / go back
 *   N       → New chat (resets chat key)
 *   1-5     → Quick-nav to main routes
 *
 * All shortcuts are suppressed when the user is typing in an input/textarea
 * or when a modifier key (Ctrl/Meta) is held (to avoid conflicts with ⌘K etc.).
 */
export function useKeyboardShortcuts() {
  const router = useRouter()
  const pathname = usePathname()
  const setViewMode = useUIStore((s) => s.setViewMode)
  const resetChat = useUIStore((s) => s.resetChat)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ignore if user is typing in an input / textarea / contenteditable
      const tag = (e.target as HTMLElement)?.tagName
      const isEditable =
        tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable

      // Allow Escape even while focused in inputs
      if (e.key === "Escape") {
        // Blur any focused input
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur()
        }
        return
      }

      // Skip all other shortcuts if typing or modifier held
      if (isEditable || e.metaKey || e.ctrlKey || e.altKey) return

      switch (e.key) {
        case "/": {
          e.preventDefault()
          // Focus the chat textarea if it exists
          const chatInput = document.querySelector<HTMLTextAreaElement>(
            'textarea[placeholder*="Ask"], textarea[placeholder*="message"], textarea[aria-label*="chat"]'
          )
          if (chatInput) {
            chatInput.focus()
            chatInput.scrollIntoView({ behavior: "smooth", block: "end" })
          }
          break
        }

        case "n":
        case "N": {
          e.preventDefault()
          resetChat()
          if (pathname !== "/operation") router.push("/operation")
          break
        }

        case "1": {
          e.preventDefault()
          setViewMode("dashboard")
          if (pathname !== "/") router.push("/")
          break
        }
        case "2": {
          e.preventDefault()
          if (pathname !== "/operation") router.push("/operation")
          break
        }
        case "3": {
          e.preventDefault()
          if (pathname !== "/mission") router.push("/mission")
          break
        }
        case "4": {
          e.preventDefault()
          if (pathname !== "/history") router.push("/history")
          break
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [router, pathname, setViewMode, resetChat])
}
