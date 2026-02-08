"use client"

import React from 'react'

export function ChatSidebar() {
  return (
    <aside className="relative z-20 hidden w-96 flex-col border-l backdrop-blur-xl 2xl:flex flex-shrink-0 transition-colors bg-[var(--chat-sidebar-bg)] border-[var(--chat-sidebar-border)]">
      <div className="border-b p-6 border-[var(--chat-sidebar-section-border)]">
        <h3 className="mb-4 text-[10px] font-black tracking-[0.3em] uppercase text-[var(--chat-sidebar-heading)]">Neural Activity</h3>

        <div className="relative overflow-hidden rounded-2xl border p-5 shadow-sm transition-colors bg-[var(--chat-sidebar-card-bg)] border-[var(--chat-sidebar-card-border)]">
          <div className="absolute top-0 left-0 h-1 w-full" style={{ background: 'var(--chat-sidebar-card-gradient)' }}></div>

          <div className="mb-2 flex items-end justify-between">
            <span className="text-2xl font-black text-[var(--chat-sidebar-value)]">92%</span>
            <span className="mb-1 rounded px-2 py-1 text-[10px] font-bold bg-[var(--chat-sidebar-stat-bg)] text-[var(--chat-sidebar-stat-text)]">OPTIMAL</span>
          </div>
          <p className="text-[10px] font-bold tracking-wider uppercase text-[var(--chat-sidebar-stat-label)]">Reasoning Capacity</p>

          <div className="mt-4 flex h-8 items-end space-x-1">
            <div className="h-[40%] flex-1 rounded-t-sm bg-[var(--chat-sidebar-bar-low)]"></div>
            <div className="h-[70%] flex-1 rounded-t-sm bg-[var(--chat-sidebar-bar-mid)]"></div>
            <div className="h-[50%] flex-1 animate-pulse rounded-t-sm bg-[var(--chat-sidebar-bar-pulse)]"></div>
            <div className="h-[80%] flex-1 rounded-t-sm bg-[var(--chat-sidebar-bar-high)]"></div>
            <div className="h-[30%] flex-1 rounded-t-sm bg-[var(--chat-sidebar-bar-bg)]"></div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <h3 className="mb-4 text-[10px] font-black tracking-[0.3em] uppercase text-[var(--chat-sidebar-heading)]">Active Artifacts</h3>

        <div className="space-y-3">
          <div className="group relative cursor-pointer rounded-xl border p-4 transition-all bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)] hover:border-[var(--chat-sidebar-artifact-hover-border)] hover:bg-[var(--chat-sidebar-artifact-hover-bg)]">
            <div className="flex items-start">
              <div className="rounded-lg p-2.5 transition-transform group-hover:scale-110 bg-[var(--chat-sidebar-artifact-icon-bg)] text-[var(--chat-sidebar-artifact-icon-text)]">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <div className="ml-3">
                <p className="text-xs font-bold text-[var(--chat-sidebar-artifact-name)]">Project_Alice_Protocol.pdf</p>
                <p className="mt-1 font-mono text-[9px] text-[var(--chat-sidebar-artifact-meta)]">10:24 AM • 2.4MB</p>
              </div>
            </div>
            <div className="absolute bottom-0 left-0 h-0.5 w-0 transition-all duration-700 group-hover:w-full bg-[var(--chat-sidebar-artifact-line)]"></div>
          </div>
        </div>
      </div>
    </aside>
  )
}
