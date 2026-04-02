"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useUIStore } from "@/shared/store/ui-store"

export function useKeyboardShortcuts() {
  const router = useRouter()
  const pathname = usePathname()
  const resetChat = useUIStore((s) => s.resetChat)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      const tag = target?.tagName
      const isEditable =
        tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable
        || target?.closest('.monaco-editor') != null

      if (e.key === "Escape") {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur()
        }
        return
      }

      if (isEditable || e.metaKey || e.ctrlKey || e.altKey) return

      switch (e.key) {
        case "/": {
          e.preventDefault()
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
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [router, pathname, resetChat])
}
