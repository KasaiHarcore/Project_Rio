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
    Cpu, 
    Settings,
    Clock,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SettingsModal } from "./settings-modal"
import { useUIStore } from "@/store/ui-store"

import { LevelBadgeSidebar } from "./LevelBadgeSidebar"

interface SidebarProps extends React.HTMLAttributes<HTMLElement> {}

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

  const handleLogout = () => {
    document.cookie = "auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT"
    router.push('/login')
  }

  const navSections = [
    {
        title: "MAIN",
        items: [
            { id: 'dashboard', label: 'Office', icon: <LayoutDashboard size={20} />, action: handleHomeClick, active: pathname === '/' },
            { id: 'operation', href: '/operation', label: 'Operation', icon: <MessageSquare size={20} />, active: pathname === '/operation' },
            { id: 'mission', href: '/mission', label: 'Mission', icon: <Map size={20} />, active: pathname === '/mission' },
        ]
    },
    {
        title: "ARCHIVE",
        items: [
            { href: '/history', label: 'History', icon: <Clock size={20} />, active: pathname.startsWith('/history') },
            { href: '/knowledge', label: 'Knowledge', icon: <Database size={20} />, active: pathname.startsWith('/knowledge') },
            { href: '/artifacts', label: 'Artifacts', icon: <FileText size={20} />, active: pathname.startsWith('/artifacts') },
            { id: 'manual', href: '/docs', label: 'Manual', icon: <Book size={20} />, active: pathname.startsWith('/docs') },
        ]
    },
    {
        title: "SYSTEM",
        items: [
            { href: '/logs', label: 'Logs', icon: <Cpu size={20} />, active: pathname.startsWith('/logs') },
            { id: 'settings', label: 'Settings', icon: <Settings size={20} />, action: () => setIsSettingsOpen(true) },
        ]
    }
  ]

  if (!sidebarOpen) return null

  return (
    <>
      <aside 
        className={cn(
          "group/sidebar relative z-20 flex w-[280px] flex-col border-r border-blue-100 bg-white/70 backdrop-blur-xl transition-all duration-300 shadow-[4px_0_24px_rgba(0,0,0,0.02)] hidden lg:flex", 
          className
        )} 
        {...props}
      >
        {/* Header / Logo Area */}
        <div className="flex flex-col items-center justify-center border-b border-blue-100/50 px-6 py-8 gap-4">
          <LevelBadgeSidebar />
          
          {/* Logo Text Hidden or smaller since Level is Main Focus now */}
          <div className="text-center mt-2 group-hover:opacity-100 transition-opacity">
             <h1 className="font-black text-slate-700 tracking-widest text-lg">SCHALE</h1>
             <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] -mt-1">Federal Investigation</p>
          </div>
        </div>

        {/* Navigation */}
        <div id="sidebar-scroll-container" className="flex-1 overflow-y-auto py-6 px-4 space-y-8 custom-scrollbar">
            {navSections.map((section, idx) => (
                <div key={idx}>
                    <h3 className="px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 pl-6 border-l-2 border-transparent">
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
                                    "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden",
                                    item.active 
                                        ? "bg-blue-50 text-[#1289F4] font-bold shadow-sm ring-1 ring-blue-100" 
                                        : "text-slate-500 hover:bg-white hover:text-slate-700 hover:shadow-sm"
                                )}
                            >
                                <div className={cn(
                                    "p-2 rounded-lg transition-colors",
                                    item.active ? "bg-white text-[#1289F4]" : "bg-slate-100 text-slate-400 group-hover:bg-blue-50 group-hover:text-[#1289F4]"
                                )}>
                                    {item.icon}
                                </div>
                                <span className="text-sm tracking-wide">{item.label}</span>
                                
                                {item.active && (
                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#1289F4] rounded-r-full" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            ))}
        </div>

        {/* User Footer */}
        <div className="p-4 border-t border-blue-100/50 bg-white/40">
            <button 
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-500 hover:shadow-sm transition-all group"
            >
                <div className="p-2 rounded-lg bg-slate-100 text-slate-400 group-hover:bg-white group-hover:text-rose-500 transition-colors">
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
