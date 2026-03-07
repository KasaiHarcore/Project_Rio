"use client"

import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import {
    Command,
    LogOut,
    LayoutDashboard,
    MessageSquare,
    Map,
    Database,
    Book,
    FileText,
    Settings,
    StickyNote,
    Terminal,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SettingsModal } from "./settings-modal"
import { useUIStore } from "@/store/ui-store"

import { LevelBadgeSidebar } from "./LevelBadgeSidebar"
import { ActiveBeam } from "@/components/ui/tracing-beam"
import { Kbd } from "@/components/ui/kbd"
import { AnimatePresence } from "framer-motion"

interface SidebarProps extends React.HTMLAttributes<HTMLElement> { }

export function Sidebar({ className, ...props }: SidebarProps) {
    const router = useRouter()
    const pathname = usePathname()
    const [isSettingsOpen, setIsSettingsOpen] = React.useState(false)
    const startMission = useUIStore((state) => state.startMission)
    const setViewMode = useUIStore((state) => state.setViewMode)
    const sidebarOpen = useUIStore((state) => state.sidebarOpen)

    const handleHomeClick = () => {
        setViewMode('dashboard')
        if (pathname !== '/') router.push('/')
    }

    const handleLogout = async () => {
        const { apiLogout } = require('@/lib/api')
        await apiLogout()
        router.push('/login')
    }

    const navSections = [
        {
            title: "COMMAND",
            items: [
                { id: 'dashboard', label: 'Office', icon: <LayoutDashboard size={20} />, action: handleHomeClick, active: pathname === '/' },
                { id: 'operation', href: '/operation', label: 'Operation', icon: <MessageSquare size={20} />, active: pathname === '/operation' },
                { id: 'mission', href: '/mission', label: 'Mission', icon: <Map size={20} />, active: pathname === '/mission' },
            ]
        },
        {
            title: "ARCHIVE",
            items: [
                { href: '/knowledge', label: 'Knowledge', icon: <Database size={20} />, active: pathname.startsWith('/knowledge') },
                { href: '/notes', label: 'Notes', icon: <StickyNote size={20} />, active: pathname.startsWith('/notes') },
                { href: '/artifacts', label: 'Artifacts', icon: <FileText size={20} />, active: pathname.startsWith('/artifacts') },
            ]
        },
        {
            title: "SYSTEM",
            items: [
                { href: '/docs', label: 'Manual', icon: <Book size={20} />, active: pathname.startsWith('/docs') },
                { href: '/logs', label: 'Logs', icon: <Terminal size={20} />, active: pathname.startsWith('/logs') },
                { id: 'settings', label: 'Settings', icon: <Settings size={20} />, action: () => setIsSettingsOpen(true) },
            ]
        }
    ]

    if (!sidebarOpen) return null

    return (
        <>
            <aside
                role="complementary"
                aria-label="Main navigation sidebar"
                className={cn(
                    "group/sidebar relative z-20 flex w-[280px] flex-col border-r transition-all duration-300 shadow-sm hidden lg:flex",
                    "bg-[var(--sidebar-chrome-bg)] border-[var(--sidebar-chrome-border)] backdrop-blur-xl",
                    className
                )}
                {...props}
            >
                {/* Header / Logo Area */}
                <div className="flex flex-col items-center justify-center border-b border-[var(--sidebar-chrome-border)] px-6 py-8 gap-4">
                    <LevelBadgeSidebar />

                    <div className="text-center mt-2 group-hover:opacity-100 transition-opacity">
                        <h1 className="font-black tracking-widest text-lg text-foreground">SCHALE</h1>
                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] -mt-1 text-[var(--sidebar-brand-sub)]">Federal Investigation</p>
                    </div>
                </div>

                {/* Navigation */}
                <nav id="sidebar-scroll-container" aria-label="Main navigation" className="flex-1 overflow-y-auto py-6 px-4 space-y-8 custom-scrollbar">
                    {navSections.map((section, idx) => (
                        <div key={idx}>
                            <h3 className="px-4 text-[10px] font-black uppercase tracking-widest mb-3 pl-6 border-l-2 border-transparent text-nav-section-text">
                                {section.title}
                            </h3>
                            <div className="space-y-1">
                                {section.items.map((item: any) => (
                                    <button
                                        key={item.label}
                                        id={item.id}
                                        onClick={() => {
                                            if (item.action) item.action()
                                            else if (item.href) router.push(item.href)
                                        }}
                                        className={cn(
                                            "w-full flex items-center gap-3 px-4 py-3 rounded-r-xl transition-all duration-200 group relative overflow-hidden",
                                            item.active
                                                ? "bg-transparent text-white font-bold border-l-[3px] border-[var(--nav-active-left-bar,var(--primary))] -ml-4 pl-[calc(1rem+1px)]"
                                                : "text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)] hover:text-[var(--nav-hover-text)] hover:shadow-sm rounded-xl"
                                        )}
                                    >
                                        <div className={cn(
                                            "p-2 rounded-lg transition-colors relative z-10",
                                            item.active
                                                ? "bg-[var(--nav-active-icon-bg)] text-[var(--nav-active-icon-text)]"
                                                : "bg-[var(--nav-icon-bg)] text-[var(--nav-icon-text)] group-hover:bg-[var(--nav-icon-hover-bg)] group-hover:text-[var(--nav-icon-hover-text)]"
                                        )}>
                                            {item.icon}
                                        </div>
                                        <span className="text-sm tracking-wide relative z-10">{item.label}</span>

                                        <AnimatePresence>
                                            {item.active && <ActiveBeam />}
                                        </AnimatePresence>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </nav>

                {/* Quick Search Hint */}
                <div className="px-4 py-3 border-t border-[var(--sidebar-chrome-border)]">
                    <button
                        onClick={() => {
                            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true }))
                        }}
                        aria-label="Open command palette"
                        className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border border-border text-sm transition-colors text-[var(--nav-item-text)] hover:bg-[var(--nav-hover-bg)]"
                    >
                        <Command size={14} aria-hidden="true" />
                        <span className="flex-1 text-left text-xs">Search...</span>
                        <Kbd>⌘K</Kbd>
                    </button>
                </div>

                {/* User Footer */}
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
            </aside>

            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </>
    )
}
