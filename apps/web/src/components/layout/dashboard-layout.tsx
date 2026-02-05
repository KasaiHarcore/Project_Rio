import React from 'react'
import { Sidebar } from './sidebar'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen bg-[#F0F7FF] font-sans text-slate-700 overflow-hidden relative">
        {/* Background Blobs */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-200/20 blur-[120px] rounded-full pointer-events-none"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-300/10 blur-[120px] rounded-full pointer-events-none"></div>

        {/* Sidebar */}
        <Sidebar className="flex-shrink-0" />

        {/* Main Content Area */}
        <main className="flex-1 relative z-10 overflow-hidden flex flex-col">
            {children}
        </main>
    </div>
  )
}
