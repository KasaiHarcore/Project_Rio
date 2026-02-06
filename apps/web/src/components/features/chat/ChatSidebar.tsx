import React from 'react'

export function ChatSidebar() {
  return (
    <aside className="relative z-20 hidden w-96 flex-col border-l border-blue-100 bg-white/60 backdrop-blur-xl 2xl:flex flex-shrink-0">
      <div className="border-b border-blue-50 p-6">
        <h3 className="mb-4 text-[10px] font-black tracking-[0.3em] text-blue-400 uppercase">Neural Activity</h3>

        <div className="relative overflow-hidden rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
          <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-blue-400 to-purple-400"></div>

          <div className="mb-2 flex items-end justify-between">
            <span className="text-2xl font-black text-slate-700">92%</span>
            <span className="mb-1 rounded bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-500">OPTIMAL</span>
          </div>
          <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Reasoning Capacity</p>

          <div className="mt-4 flex h-8 items-end space-x-1">
            <div className="h-[40%] flex-1 rounded-t-sm bg-blue-100"></div>
            <div className="h-[70%] flex-1 rounded-t-sm bg-blue-200"></div>
            <div className="h-[50%] flex-1 animate-pulse rounded-t-sm bg-blue-500"></div>
            <div className="h-[80%] flex-1 rounded-t-sm bg-blue-300"></div>
            <div className="h-[30%] flex-1 rounded-t-sm bg-blue-100"></div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <h3 className="mb-4 text-[10px] font-black tracking-[0.3em] text-blue-400 uppercase">Active Artifacts</h3>

        <div className="space-y-3">
          <div className="group relative cursor-pointer rounded-xl border border-blue-50 bg-white/50 p-4 transition-all hover:border-blue-300 hover:bg-white">
            <div className="flex items-start">
              <div className="rounded-lg bg-blue-50 p-2.5 text-blue-500 transition-transform group-hover:scale-110">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <div className="ml-3">
                <p className="text-xs font-bold text-slate-700">Project_Alice_Protocol.pdf</p>
                <p className="mt-1 font-mono text-[9px] text-slate-400">10:24 AM • 2.4MB</p>
              </div>
            </div>
            <div className="absolute bottom-0 left-0 h-0.5 w-0 bg-blue-500 transition-all duration-700 group-hover:w-full"></div>
          </div>
        </div>
      </div>
    </aside>
  )
}
