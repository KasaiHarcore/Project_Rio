import React from 'react'
import { FileText } from 'lucide-react'

export function ChatSidebar() {
  return (
    <aside className="hidden 2xl:flex w-80 bg-white border-l border-blue-100 flex-col z-20">
      <div className="p-6 border-b border-blue-50 bg-blue-50/20">
        <h3 className="text-[11px] font-black text-blue-500 uppercase tracking-[0.2em] mb-4">Neural Activity</h3>
        <div className="p-4 bg-white border border-blue-100 rounded-2xl shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Reasoning Mode</span>
            <span className="text-[10px] font-mono text-green-500 bg-green-50 px-2 py-0.5 rounded">IDLE</span>
          </div>
          <div className="h-2 w-full bg-blue-50 rounded-full overflow-hidden">
            <div className="h-full bg-blue-400 w-1/3 animate-pulse"></div>
          </div>
        </div>
      </div>
      
      <div className="p-6 flex-1">
        <h3 className="text-[11px] font-black text-blue-500 uppercase tracking-[0.2em] mb-4">Tactical Artifacts</h3>
        <div className="space-y-3">
          <div className="p-3 border border-blue-50 rounded-xl bg-white hover:border-blue-200 transition-all cursor-pointer group">
            <div className="flex items-center">
              <div className="p-2 bg-blue-50 text-blue-500 rounded-lg group-hover:bg-blue-500 group-hover:text-white transition-all">
                <FileText className="h-4 w-4" />
              </div>
              <div className="ml-3">
                <p className="text-[11px] font-bold text-slate-700 truncate">Q4_Tactical_Brief.pdf</p>
                <p className="text-[9px] text-slate-400">1.2 MB • PDF</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
