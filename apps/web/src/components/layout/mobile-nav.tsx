"use client"

import React, { useState } from "react"
import { useRouter, usePathname } from "next/navigation"
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
  LogOut,
  Menu,
  Search,
  StickyNote,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useUIStore } from "@/store/ui-store"
import { Sheet } from "@/components/ui/sheet"
import { LevelBadgeSidebar } from "@/components/layout/LevelBadgeSidebar"
import { AnimatePresence } from "framer-motion"
import { ActiveBeam } from "@/components/ui/tracing-beam"
import { Kbd } from "@/components/ui/kbd"

export function MobileNav() {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  const setViewMode = useUIStore((state) => state.setViewMode)

  const handleNav = (path: string, action?: () => void) => {
    setOpen(false)
    if (action) action()
    else if (pathname !== path) router.push(path)
  }

  const handleHomeClick = () => {
    setViewMode("dashboard")
    handleNav("/")
  }

  const handleLogout = async () => {
    const { apiLogout } = require('@/lib/api')
    await apiLogout()
    handleNav("/login")
  }

  const navSections = [
    {
      title: "COMMAND",
      items: [
        { label: "Office", icon: <LayoutDashboard size={20} />, action: handleHomeClick, active: pathname === "/" },
        { label: "Operation", icon: <MessageSquare size={20} />, href: "/operation", active: pathname === "/operation" },
        { label: "Mission", icon: <Map size={20} />, href: "/mission", active: pathname === "/mission" },
      ],
    },
    {
      title: "ARCHIVE",
      items: [
        { label: "Knowledge", icon: <Database size={20} />, href: "/knowledge", active: pathname.startsWith("/knowledge") },
        { label: "Notes", icon: <StickyNote size={20} />, href: "/notes", active: pathname.startsWith("/notes") },
        { label: "Artifacts", icon: <FileText size={20} />, href: "/artifacts", active: pathname.startsWith("/artifacts") },
      ],
    },
    {
      title: "SYSTEM",
      items: [
        { label: "Manual", icon: <Book size={20} />, href: "/docs", active: pathname.startsWith("/docs") },
        { label: "Logs", icon: <Terminal size={20} />, href: "/logs", active: pathname.startsWith("/logs") },
        { label: "Settings", icon: <Settings size={20} />, action: () => setOpen(false) },
      ],
    },
  ]

  return (
    <>
      {/* Mobile Top Bar — only shows below lg breakpoint */}
      <div className="flex lg:hidden items-center justify-between px-4 py-3 border-b z-30 flex-shrink-0 bg-[var(--sidebar-chrome-bg)] border-[var(--sidebar-chrome-border)] backdrop-blur-xl">
        <button
          onClick={() => setOpen(true)}
          className="p-2 rounded-xl transition-colors text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)]"
          aria-label="Open navigation menu"
        >
          <Menu size={22} />
        </button>

        <h1 className="text-sm font-black tracking-widest text-foreground">
          SCHALE
        </h1>

        <button
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }))
          }}
          className="p-2 rounded-xl transition-colors text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)]"
          aria-label="Search commands"
        >
          <Search size={20} />
        </button>
      </div>

      {/* Sheet Drawer */}
      <Sheet open={open} onOpenChange={setOpen} side="left">
        {/* Header */}
        <div className="flex flex-col items-center justify-center border-b border-[var(--sidebar-chrome-border)] px-6 py-8 gap-4">
          <LevelBadgeSidebar />
          <div className="text-center mt-2">
            <h1 className="font-black tracking-widest text-lg text-foreground">
              SCHALE
            </h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] -mt-1 text-[var(--sidebar-brand-sub)]">
              Federal Investigation
            </p>
          </div>
        </div>

        {/* Nav Items */}
        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 custom-scrollbar">
          {navSections.map((section, idx) => (
            <div key={idx}>
              <h3 className="px-4 text-[10px] font-black uppercase tracking-widest mb-3 pl-6 border-l-2 border-transparent text-nav-section-text">
                {section.title}
              </h3>
              <div className="space-y-1">
                {section.items.map((item: any) => (
                  <button
                    key={item.label}
                    onClick={() => {
                      if (item.action) item.action()
                      else if (item.href) handleNav(item.href)
                    }}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden",
                      item.active
                        ? "bg-[var(--nav-active-bg)] text-[var(--nav-active-text)] font-bold shadow-sm ring-1 ring-[var(--nav-active-ring)]"
                        : "text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)] hover:text-[var(--nav-hover-text)] hover:shadow-sm"
                    )}
                  >
                    <div
                      className={cn(
                        "p-2 rounded-lg transition-colors relative z-10",
                        item.active
                          ? "bg-[var(--nav-active-icon-bg)] text-[var(--nav-active-icon-text)]"
                          : "bg-[var(--nav-icon-bg)] text-[var(--nav-icon-text)] group-hover:bg-[var(--nav-icon-hover-bg)] group-hover:text-[var(--nav-icon-hover-text)]"
                      )}
                    >
                      {item.icon}
                    </div>
                    <span className="text-sm tracking-wide relative z-10">{item.label}</span>
                    <AnimatePresence>{item.active && <ActiveBeam />}</AnimatePresence>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Quick Search Hint */}
        <div className="px-4 py-3 border-t border-[var(--sidebar-chrome-border)]">
          <button
            onClick={() => {
              setOpen(false)
              setTimeout(() => {
                document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }))
              }, 300)
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border border-border text-sm transition-colors text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)]"
          >
            <Search size={14} />
            <span className="flex-1 text-left text-xs">Search commands...</span>
            <Kbd>⌘K</Kbd>
          </button>
        </div>

        {/* Logout */}
        <div className="p-4 border-t border-[var(--sidebar-footer-border)] bg-[var(--sidebar-footer-bg)]">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all group text-[var(--nav-item-text)] hover:bg-destructive/10 hover:text-destructive"
          >
            <div className="p-2 rounded-lg transition-colors bg-[var(--nav-icon-bg)] text-[var(--nav-icon-text)] group-hover:bg-destructive/10 group-hover:text-destructive">
              <LogOut size={18} />
            </div>
            <span className="text-sm font-bold">Disconnect</span>
          </button>
        </div>
      </Sheet>
    </>
  )
}
