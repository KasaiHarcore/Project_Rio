"use client"

import React from 'react'
import { cn } from '@/shared/lib/utils'
import { ExternalLink, FileText, Share2, MoreHorizontal, Play } from 'lucide-react'
import type { MessageSource, WebSource, DocSource } from '@/features/chat/store'

/**
 * SourcePreviewCard — rich citation card shown inside the tree-view
 * DetailPanel. Two variants:
 *
 *   - web: Messenger / iMessage-style link unfurl — URL header, og:image
 *          hero, title, snippet, site_name, timestamp.
 *   - doc: document attachment card — thumbnail preview + filename footer
 *          with share/more actions. Modeled on the Facebook/iMessage
 *          document share card.
 */

interface SourcePreviewCardProps {
  source: MessageSource
}

export function SourcePreviewCard({ source }: SourcePreviewCardProps) {
  return source.kind === 'web'
    ? <WebPreviewCard source={source} />
    : <DocPreviewCard source={source} />
}

/* ─── Web variant ────────────────────────────────────────────────── */

function domainFromUrl(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

function formatClockTime(ms: number): string {
  try {
    return new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function WebPreviewCard({ source }: { source: WebSource }) {
  const { url, title, snippet, ogImage, siteName, timestamp } = source
  const domain = siteName ?? domainFromUrl(url)
  const time = formatClockTime(timestamp)

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group block rounded-2xl border border-slate-700/50 bg-[#0d1520]/70 overflow-hidden",
        "hover:border-sky-500/50 hover:bg-[#0d1520] transition-colors",
      )}
    >
      {/* URL header */}
      <div className="px-3 pt-2 pb-1.5 text-[10px] font-medium text-sky-400 truncate">
        {url}
      </div>

      {/* Hero image */}
      {ogImage && (
        <div className="relative aspect-[16/9] bg-slate-900/80 overflow-hidden">
          <img
            src={ogImage}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => { (e.currentTarget.style.display = 'none') }}
          />
        </div>
      )}

      {/* Body */}
      <div className="px-3 py-2.5">
        <p className="text-[11px] font-semibold text-slate-100 leading-snug line-clamp-2 mb-1">
          {title}
        </p>
        {snippet && (
          <p className="text-[10px] text-slate-400 leading-snug line-clamp-3 mb-1.5">
            {snippet}
          </p>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-sky-400 font-medium truncate">
            {domain}
          </span>
          <ExternalLink className="h-2.5 w-2.5 text-sky-400/70 group-hover:text-sky-300" />
        </div>
      </div>

      {/* Timestamp footer */}
      {time && (
        <div className="px-3 pb-2 text-[9px] font-mono text-slate-600">
          {time}
        </div>
      )}
    </a>
  )
}

/* ─── Doc variant ────────────────────────────────────────────────── */

function DocPreviewCard({ source }: { source: DocSource }) {
  const { filename, title, thumbnailUrl, excerpt, page, source: origin } = source

  return (
    <div
      className={cn(
        "group rounded-2xl border border-slate-700/50 bg-[#0d1520]/70 overflow-hidden",
        "hover:border-cyan-500/50 hover:bg-[#0d1520] transition-colors",
      )}
    >
      {/* Thumbnail / document preview */}
      <div className="relative aspect-[4/3] bg-[#141b28] overflow-hidden">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => { (e.currentTarget.style.display = 'none') }}
          />
        ) : (
          <div className="absolute inset-0 p-3 text-[8px] leading-snug text-slate-400/80 overflow-hidden">
            {title && (
              <p className="text-[10px] font-bold text-slate-200 mb-1 line-clamp-1">
                {title}
              </p>
            )}
            <p className="line-clamp-[10] whitespace-pre-wrap">
              {excerpt ?? ''}
            </p>
          </div>
        )}
        {/* Play affordance — visual parity with the reference screenshot. */}
        <button
          type="button"
          aria-label="Open preview"
          onClick={(e) => e.stopPropagation()}
          className="absolute bottom-2 right-2 w-7 h-7 rounded-full bg-white/90 text-slate-900 flex items-center justify-center shadow-md hover:bg-white transition-colors"
        >
          <Play className="h-3.5 w-3.5 fill-slate-900" />
        </button>
      </div>

      {/* Footer — filename + actions */}
      <div className="flex items-center gap-2 px-3 py-2 bg-[#111a26] border-t border-slate-700/40">
        <div className="w-7 h-7 rounded-md bg-slate-800 flex items-center justify-center flex-shrink-0">
          <FileText className="h-3.5 w-3.5 text-slate-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold text-slate-100 truncate">
            {filename}
          </p>
          {(origin || page != null) && (
            <p className="text-[9px] text-slate-500 truncate">
              {[origin, page != null ? `page ${page}` : null].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <button
          type="button"
          aria-label="Share"
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
        >
          <Share2 className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          aria-label="More"
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
