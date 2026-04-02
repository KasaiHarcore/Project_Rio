"use client"

import React from 'react'

export function ChatHeader() {
  return (
    <header className="relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 transition-colors bg-[var(--chat-header-bg)] border-[var(--chat-header-border)]">
      <div className="absolute bottom-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent to-transparent opacity-50" style={{ backgroundImage: `linear-gradient(to right, transparent, var(--chat-header-line), transparent)` }}></div>

      <div className="flex items-center gap-6">
        <div className="flex items-center rounded-lg border px-4 py-1.5 shadow-sm transition-colors bg-[var(--chat-header-status-bg)] border-[var(--chat-header-status-border)]">
          <div className="mr-3 h-2 w-2 rounded-full" style={{ backgroundColor: 'var(--chat-header-dot)', boxShadow: `0 0 8px var(--chat-header-dot-shadow)` }}></div>
          <span className="font-mono text-[10px] font-bold uppercase text-[var(--chat-header-status-text)]">System: <span className="text-[var(--chat-header-status-value)]">Stable</span></span>
        </div>
        <div className="h-4 w-[1px] bg-[var(--chat-header-divider)]"></div>
        <span className="font-mono text-[10px] text-[var(--chat-header-latency)]">LATENCY: 24ms</span>
      </div>

      <div className="flex items-center gap-3">
        <button aria-label="Search messages" className="flex h-8 w-8 items-center justify-center rounded-lg transition-all text-[var(--chat-header-btn-text)] hover:bg-[var(--chat-header-btn-hover-bg)] hover:text-[var(--chat-header-btn-hover-text)]">
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        </button>
        <button aria-label="Chat settings" className="flex h-8 w-8 items-center justify-center rounded-lg transition-all text-[var(--chat-header-btn-text)] hover:bg-[var(--chat-header-btn-hover-bg)] hover:text-[var(--chat-header-btn-hover-text)]">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </header>
  )
}
