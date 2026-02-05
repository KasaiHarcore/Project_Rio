import React from 'react'
import { MoreVertical, RefreshCw, Activity, Clock, ShieldCheck } from 'lucide-react'

export function ChatHeader() {
  return (
    <header className="h-16 border-b border-blue-100 bg-white/50 backdrop-blur-md flex items-center justify-between px-8 transition-all">
      <div className="flex items-center">
        <div className="flex items-center bg-white/80 border border-blue-50 px-3 py-1.5 rounded-full shadow-sm">
          <div className="relative flex h-2 w-2 mr-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </div>
          <h2 className="text-xs font-black text-slate-800 uppercase tracking-tighter">
            Active Sync: <span className="text-blue-500">Aris_v2</span>
          </h2>
        </div>
        
        <div className="hidden md:flex ml-8 items-center space-x-0">
          <div className="px-4 border-l border-blue-100/50">
            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] leading-tight">Latency</p>
            <p className="text-[11px] font-mono font-bold text-blue-500 tracking-tighter">
              24<span className="text-[8px] ml-0.5 opacity-70">MS</span>
            </p>
          </div>
        
          <div className="px-4 border-l border-blue-100/50">
            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] leading-tight">Uptime</p>
            <p className="text-[11px] font-mono font-bold text-slate-700 tracking-tighter">04:22:12</p>
          </div>
        
          <div className="px-4 border-l border-blue-100/50 border-r">
            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] leading-tight">Health</p>
            <div className="flex items-center space-x-2">
              <span className="text-[11px] font-mono font-bold text-green-500 tracking-tighter">
                100<span className="text-[8px] ml-0.5 opacity-70">%</span>
              </span>
              <div className="w-8 h-1 bg-slate-100 rounded-full overflow-hidden hidden lg:block">
                <div className="h-full bg-green-500 w-full"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <div className="h-6 w-[1px] bg-blue-100"></div>
        <button className="p-2.5 text-slate-400 hover:text-blue-500 hover:bg-white rounded-xl transition-all border border-transparent hover:border-blue-100">
          <MoreVertical className="h-5 w-5" />
        </button>
        <div className="h-6 w-[1px] bg-blue-100"></div>
        <button className="p-2.5 text-slate-400 hover:text-blue-500 hover:bg-white rounded-xl transition-all border border-transparent hover:border-blue-100">
            <RefreshCw className="h-5 w-5" />
        </button>
      </div>
    </header>
  )
}
