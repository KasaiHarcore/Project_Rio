"use client"

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard,
  MessageSquare,
  Map,
  Clock,
  Database,
  FileText,
  Book,
  Terminal,
  Settings,
  Plus,
  Search,
  LogOut,
  ArrowRight,
  Command,
  StickyNote,
  Share2,
} from "lucide-react"
import { useRouter, usePathname } from "next/navigation"
import { cn } from "@/shared/lib/utils"
import { useUIStore } from "@/shared/store/ui-store"
import { Kbd } from "@/components/ui/kbd"

interface CommandItem {
  id: string
  label: string
  description?: string
  icon: React.ReactNode
  section: string
  keywords: string[]
  action: () => void
}

/** Searchable content items — conversations, documents, artifacts */
interface SearchResult {
  id: string
  title: string
  preview: string
  type: "conversation" | "document" | "artifact"
  icon: React.ReactNode
  date: string
  action: () => void
}

type PaletteMode = "commands" | "search"

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [mode, setMode] = useState<PaletteMode>("commands")
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const pathname = usePathname()
  const { startMission, setViewMode } = useUIStore()

  // Register global ⌘K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("")
      setSelectedIndex(0)
      setMode("commands")
      // Small delay for animation
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  const close = useCallback(() => setOpen(false), [])

  const navigate = useCallback(
    (path: string) => {
      close()
      if (pathname !== path) router.push(path)
    },
    [close, pathname, router]
  )

  // All available commands
  const commands: CommandItem[] = useMemo(
    () => [
      // Navigation
      {
        id: "nav-office",
        label: "Office",
        description: "Go to dashboard",
        icon: <LayoutDashboard size={18} />,
        section: "Navigation",
        keywords: ["home", "dashboard", "office", "main"],
        action: () => { close(); setViewMode("dashboard"); navigate("/") },
      },
      {
        id: "nav-operation",
        label: "Operation",
        description: "Chat operations",
        icon: <MessageSquare size={18} />,
        section: "Navigation",
        keywords: ["chat", "operation", "message", "talk"],
        action: () => navigate("/operation"),
      },
      {
        id: "nav-mission",
        label: "Mission",
        description: "Task board",
        icon: <Map size={18} />,
        section: "Navigation",
        keywords: ["mission", "task", "daily", "weekly"],
        action: () => navigate("/mission"),
      },
      {
        id: "nav-knowledge",
        label: "Knowledge",
        description: "Document repository",
        icon: <Database size={18} />,
        section: "Navigation",
        keywords: ["knowledge", "document", "file", "upload", "rag"],
        action: () => navigate("/knowledge"),
      },
      {
        id: "nav-notes",
        label: "Notes",
        description: "Personal note-taking",
        icon: <StickyNote size={18} />,
        section: "Navigation",
        keywords: ["notes", "note", "markdown", "write"],
        action: () => navigate("/notes"),
      },
      {
        id: "nav-artifacts",
        label: "Artifacts",
        description: "Generated content",
        icon: <FileText size={18} />,
        section: "Navigation",
        keywords: ["artifact", "generated", "code", "output"],
        action: () => navigate("/artifacts"),
      },
      {
        id: "nav-graph",
        label: "Note Graph",
        description: "Knowledge visualization",
        icon: <Share2 size={18} />,
        section: "Navigation",
        keywords: ["graph", "links", "visualization", "connections", "network"],
        action: () => navigate("/graph"),
      },
      {
        id: "nav-manual",
        label: "Manual",
        description: "Documentation",
        icon: <Book size={18} />,
        section: "Navigation",
        keywords: ["manual", "docs", "help", "guide"],
        action: () => navigate("/docs"),
      },
      {
        id: "nav-logs",
        label: "Logs",
        description: "System logs",
        icon: <Terminal size={18} />,
        section: "Navigation",
        keywords: ["logs", "system", "debug", "trace"],
        action: () => navigate("/logs"),
      },
      // Actions
      {
        id: "action-new-chat",
        label: "New Chat",
        description: "Start a new conversation",
        icon: <Plus size={18} />,
        section: "Actions",
        keywords: ["new", "chat", "conversation", "start"],
        action: () => { close(); startMission() },
      },
      {
        id: "action-settings",
        label: "Settings",
        description: "Open settings",
        icon: <Settings size={18} />,
        section: "Actions",
        keywords: ["settings", "config", "preference", "account"],
        action: () => { close(); /* settings modal trigger would go here */ },
      },
      {
        id: "action-logout",
        label: "Disconnect",
        description: "Sign out of your account",
        icon: <LogOut size={18} />,
        section: "Actions",
        keywords: ["logout", "signout", "disconnect", "exit"],
        action: async () => {
          close()
          const { apiLogout } = require('@/features/auth/api')
          await apiLogout()
          router.push("/login")
        },
      },
    ],
    [close, navigate, startMission, setViewMode, router]
  )

  // ─── Searchable Content ────────────────────────────────────
  const searchableContent: SearchResult[] = useMemo(() => [
    { id: "s-conv-1", title: "Binary Search Implementation", preview: "Can you help me implement a binary search algorithm in Python?", type: "conversation", icon: <MessageSquare size={16} />, date: "Feb 5", action: () => { close(); router.push("/operation") } },
    { id: "s-conv-2", title: "Machine Learning Study Plan", preview: "I need a 30-day study plan for machine learning fundamentals...", type: "conversation", icon: <MessageSquare size={16} />, date: "Feb 4", action: () => { close(); router.push("/operation") } },
    { id: "s-conv-3", title: "Neural Network Architecture", preview: "Explain the architecture of a convolutional neural network...", type: "conversation", icon: <MessageSquare size={16} />, date: "Feb 3", action: () => { close(); router.push("/operation") } },
    { id: "s-conv-4", title: "API Design Best Practices", preview: "What are the best practices for designing RESTful APIs?", type: "conversation", icon: <MessageSquare size={16} />, date: "Feb 2", action: () => { close(); router.push("/operation") } },
    // Documents
    { id: "s-doc-1", title: "Machine Learning Fundamentals.pdf", preview: "Comprehensive guide covering supervised and unsupervised learning", type: "document", icon: <FileText size={16} />, date: "Feb 4", action: () => { close(); router.push("/knowledge") } },
    { id: "s-doc-2", title: "Neural Networks Guide.pdf", preview: "Deep dive into neural network architectures and training", type: "document", icon: <FileText size={16} />, date: "Feb 3", action: () => { close(); router.push("/knowledge") } },
    { id: "s-doc-3", title: "Python Cheatsheet.md", preview: "Quick reference for Python syntax, data structures, and patterns", type: "document", icon: <FileText size={16} />, date: "Feb 2", action: () => { close(); router.push("/knowledge") } },
    // Artifacts
    { id: "s-art-1", title: "Binary Search Algorithm", preview: "def binary_search(arr, target): lo, hi = 0, len(arr)-1...", type: "artifact", icon: <FileText size={16} />, date: "Feb 5", action: () => { close(); router.push("/artifacts") } },
    { id: "s-art-2", title: "Study Plan Template", preview: "Week 1: Linear algebra basics, Week 2: Probability theory...", type: "artifact", icon: <FileText size={16} />, date: "Feb 4", action: () => { close(); router.push("/artifacts") } },
  ], [close, router])

  // Filter commands based on query
  const filtered = useMemo(() => {
    if (!query.trim()) return commands
    const q = query.toLowerCase()
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.description?.toLowerCase().includes(q) ||
        cmd.keywords.some((kw) => kw.includes(q))
    )
  }, [query, commands])

  // Group by section
  const grouped = useMemo(() => {
    const sections: Record<string, CommandItem[]> = {}
    for (const item of filtered) {
      if (!sections[item.section]) sections[item.section] = []
      sections[item.section].push(item)
    }
    return sections
  }, [filtered])

  // Flat list for keyboard navigation
  const flatList = useMemo(() => filtered, [filtered])

  // Filtered search results
  const searchResults = useMemo(() => {
    if (mode !== "search" || !query.trim()) return []
    const q = query.toLowerCase()
    return searchableContent.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.preview.toLowerCase().includes(q)
    )
  }, [query, mode, searchableContent])

  useEffect(() => {
    if (query.length >= 3 && filtered.length === 0 && mode === "commands") {
      setMode("search")
      setSelectedIndex(0)
    }
  }, [query, filtered.length, mode])

  // Current active list for keyboard nav
  const activeList = mode === "search" ? searchResults : flatList

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((prev) => Math.min(prev + 1, activeList.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((prev) => Math.max(prev - 1, 0))
    } else if (e.key === "Enter") {
      e.preventDefault()
      activeList[selectedIndex]?.action()
    } else if (e.key === "Escape") {
      close()
    } else if (e.key === "Tab") {
      e.preventDefault()
      setMode((m) => m === "commands" ? "search" : "commands")
      setSelectedIndex(0)
    }
  }

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`)
    el?.scrollIntoView({ block: "nearest" })
  }, [selectedIndex])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={close}
            className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm"
          />

          {/* Palette */}
          <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh] px-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -10 }}
              transition={{ duration: 0.15, ease: [0.32, 0.72, 0, 1] }}
              className="pointer-events-auto w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
              onKeyDown={handleKeyDown}
            >
              {/* Search Input */}
              <div className="flex items-center gap-3 border-b border-border px-4">
                <Search size={18} className="text-muted-foreground flex-shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={mode === "search" ? "Search conversations, documents, artifacts..." : "Search commands..."}
                  className="flex-1 bg-transparent py-4 text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground/50"
                />
                <Kbd>Esc</Kbd>
              </div>

              {/* Mode Tabs */}
              <div className="flex items-center gap-1 px-3 pt-2">
                <button
                  onClick={() => { setMode("commands"); setSelectedIndex(0) }}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-colors",
                    mode === "commands"
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/50 hover:text-muted-foreground"
                  )}
                >
                  Commands
                </button>
                <button
                  onClick={() => { setMode("search"); setSelectedIndex(0) }}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-colors",
                    mode === "search"
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/50 hover:text-muted-foreground"
                  )}
                >
                  Search
                </button>
                <span className="ml-auto text-[10px] text-muted-foreground/40 flex items-center gap-1">
                  <Kbd>Tab</Kbd> switch
                </span>
              </div>

              {/* Results */}
              <div ref={listRef} className="max-h-[320px] overflow-y-auto p-2 custom-scrollbar">
                {mode === "commands" ? (
                  /* ─── Commands Mode ─── */
                  flatList.length === 0 ? (
                    <div className="py-8 text-center">
                      <p className="text-sm text-muted-foreground">No commands found</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">
                        Press <Kbd>Tab</Kbd> to search content instead
                      </p>
                    </div>
                  ) : (
                    Object.entries(grouped).map(([section, items]) => (
                      <div key={section}>
                        <div className="px-3 py-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                            {section}
                          </span>
                        </div>
                        {items.map((item) => {
                          const globalIndex = flatList.indexOf(item)
                          const isSelected = globalIndex === selectedIndex
                          return (
                            <button
                              key={item.id}
                              data-index={globalIndex}
                              onClick={item.action}
                              onMouseEnter={() => setSelectedIndex(globalIndex)}
                              className={cn(
                                "w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                                isSelected
                                  ? "bg-primary/10 text-foreground"
                                  : "text-muted-foreground hover:text-foreground"
                              )}
                            >
                              <div
                                className={cn(
                                  "flex h-9 w-9 items-center justify-center rounded-lg transition-colors flex-shrink-0",
                                  isSelected
                                    ? "bg-primary/15 text-primary"
                                    : "bg-muted/60 text-muted-foreground"
                                )}
                              >
                                {item.icon}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold truncate">{item.label}</p>
                                {item.description && (
                                  <p className="text-xs text-muted-foreground/70 truncate">{item.description}</p>
                                )}
                              </div>
                              {isSelected && (
                                <ArrowRight size={14} className="text-primary flex-shrink-0" />
                              )}
                            </button>
                          )
                        })}
                      </div>
                    ))
                  )
                ) : (
                  /* ─── Search Mode ─── */
                  !query.trim() ? (
                    <div className="py-8 text-center">
                      <Search size={32} className="mx-auto text-muted-foreground/30 mb-3" />
                      <p className="text-sm text-muted-foreground">Search across all your content</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">Conversations, documents, and artifacts</p>
                    </div>
                  ) : searchResults.length === 0 ? (
                    <div className="py-8 text-center">
                      <p className="text-sm text-muted-foreground">No results for &ldquo;{query}&rdquo;</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">Try different keywords</p>
                    </div>
                  ) : (
                    <>
                      <div className="px-3 py-2">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
                          {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
                        </span>
                      </div>
                      {searchResults.map((result, idx) => {
                        const isSelected = idx === selectedIndex
                        const typeLabel = result.type === "conversation" ? "Chat" : result.type === "document" ? "Doc" : "Artifact"
                        const typeColor = result.type === "conversation" ? "text-blue-400" : result.type === "document" ? "text-emerald-400" : "text-amber-400"
                        return (
                          <button
                            key={result.id}
                            data-index={idx}
                            onClick={result.action}
                            onMouseEnter={() => setSelectedIndex(idx)}
                            className={cn(
                              "w-full flex items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors",
                              isSelected
                                ? "bg-primary/10 text-foreground"
                                : "text-muted-foreground hover:text-foreground"
                            )}
                          >
                            <div
                              className={cn(
                                "flex h-9 w-9 items-center justify-center rounded-lg transition-colors flex-shrink-0",
                                isSelected
                                  ? "bg-primary/15 text-primary"
                                  : "bg-muted/60 text-muted-foreground"
                              )}
                            >
                              {result.icon}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-bold truncate">{result.title}</p>
                                <span className={cn("text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted/60", typeColor)}>
                                  {typeLabel}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground/60 truncate mt-0.5">{result.preview}</p>
                            </div>
                            <span className="text-[10px] text-muted-foreground/40 flex-shrink-0">{result.date}</span>
                          </button>
                        )
                      })}
                    </>
                  )
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground/60">
                  <span className="flex items-center gap-1"><Kbd>↑</Kbd><Kbd>↓</Kbd> navigate</span>
                  <span className="flex items-center gap-1"><Kbd>↵</Kbd> select</span>
                  <span className="flex items-center gap-1"><Kbd>Esc</Kbd> close</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
                  <Command size={10} />
                  <span className="font-bold">SCHALE</span>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
