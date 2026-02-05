"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { 
  Command, 
  Plus, 
  Database, 
  Layers, 
  Clock, 
  ChevronLeft,
  Settings,
  LogOut
} from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps extends React.HTMLAttributes<HTMLElement> {}

export function Sidebar({ className, ...props }: SidebarProps) {
  const router = useRouter()
  // const { activeView, setActiveView } = useUIStore() 
  const activeView = 'chat'; // Placeholder

  const handleLogout = () => {
    // Expire the auth cookie
    document.cookie = "auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT"
    router.push('/login')
  }

  return (
    <aside 
      className={cn(
        "w-20 lg:w-72 bg-white/40 backdrop-blur-2xl border-r border-blue-100/50 flex flex-col py-6 transition-all duration-500 relative group/sidebar z-20", 
        className
      )} 
      {...props}
    >
      {/* Header */}
      <div className="px-6 mb-8 flex items-center">
        <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200 flex-shrink-0">
          <Command className="h-6 w-6 text-white" />
        </div>
        <div className="ml-4 hidden lg:block">
          <p className="font-black text-lg leading-none tracking-tighter text-slate-800">
            SCHALE <span className="text-blue-500 font-mono text-[10px] bg-blue-50 px-1 rounded">OS_v2.0</span>
          </p>
          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.3em] mt-1">
            General Operations
          </p>
        </div>
      </div>

      {/* Main Actions */}
      <div className="px-4 space-y-1 mb-8">
        <button className="w-full flex items-center p-3 bg-blue-500 text-white rounded-2xl shadow-lg shadow-blue-100 font-bold text-sm group hover:scale-[1.02] transition-all">
          <Plus className="h-5 w-5 flex-shrink-0" />
          <span className="ml-3 truncate hidden lg:block">New Operation</span>
        </button>
        
        <nav className="pt-4 space-y-1">
          <button 
            className={cn(
              "w-full flex items-center p-3 rounded-xl transition-all font-semibold text-sm",
              activeView === 'knowledge' 
                ? "bg-blue-50 text-blue-600" 
                : "text-slate-500 hover:bg-blue-50 hover:text-blue-600"
            )}
           // onClick={() => setActiveView('knowledge')}
          >
            <Database className="h-5 w-5" />
            <span className="ml-3 hidden lg:block">Knowledge Base</span>
          </button>
          
          <button 
             className={cn(
              "w-full flex items-center p-3 rounded-xl transition-all font-semibold text-sm",
              activeView === 'artifacts' 
                ? "bg-blue-50 text-blue-600" 
                : "text-slate-500 hover:bg-blue-50 hover:text-blue-600"
            )}
            // onClick={() => setActiveView('artifacts')}
          >
            <Layers className="h-5 w-5" />
            <span className="ml-3 hidden lg:block">Artifacts</span>
          </button>
        </nav>
      </div>

      {/* Operational History */}
      <div className="flex-1 px-4 overflow-y-auto">
        <div className="flex items-center justify-between px-2 mb-4">
          <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest hidden lg:block">
            Operational History
          </span>
          <button className="text-slate-300 hover:text-blue-500">
            <Clock className="h-4 w-4" />
          </button>
        </div>
        
        <div className="space-y-2 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
          {/* Mock History Item */}
          <button className="w-full group flex flex-col p-3 bg-white border border-blue-100 rounded-xl shadow-sm hover:border-blue-400 transition-all text-left relative overflow-hidden">
             <div className="absolute top-0 right-0 p-1">
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
             </div>
             <span className="text-[10px] font-black text-slate-800 truncate block">
               Neural Link Alpha
             </span>
             <span className="text-[8px] font-mono text-slate-400 uppercase tracking-tighter mt-1">
               Last Sync: 2m ago
             </span>
          </button>
        </div>
      </div>

      {/* User / Footer */}
      <div className="mt-auto p-4 border-t border-blue-50 relative">
        <div className="flex items-center p-2 rounded-xl hover:bg-blue-50 transition-colors cursor-pointer group">
            <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-500">
                S
            </div>
            <div className="ml-3 hidden lg:block">
                <p className="text-xs font-bold text-slate-700">Sensei</p>
                <p className="text-[9px] text-slate-400">Online</p>
            </div>
            <div className="ml-auto flex items-center space-x-1">
                <Settings className="h-4 w-4 text-slate-400 hover:text-blue-500 hidden lg:block" />
                <button onClick={handleLogout} title="Sign Out">
                    <LogOut className="h-4 w-4 text-slate-400 hover:text-red-500 hidden lg:block" />
                </button>
            </div>
        </div>
      </div>
    </aside>
  )
}
