"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Book, Sparkles } from "lucide-react"
import { motion } from "framer-motion"
import { BentoCard } from "@/components/ui/bento-card"
import { FEATURE_DOCS } from "@/features/docs/data"

export function DocsView() {
  const [selectedFeature, setSelectedFeature] = React.useState(0)

  return (
    <DashboardLayout>
      <PageTransition>
        <div className="flex h-full overflow-hidden">
          {/* Left navigation */}
          <aside className="w-72 border-r border-border bg-card/30 backdrop-blur-sm overflow-y-auto custom-scrollbar flex-shrink-0">
            <div className="p-4 border-b border-border">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <Book className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-lg font-bold">User Manual</h2>
              </div>
              <p className="text-xs text-muted-foreground">
                Complete feature guide
              </p>
            </div>

            <nav className="p-3 space-y-1">
              {FEATURE_DOCS.map((feature, idx) => {
                const Icon = feature.icon
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedFeature(idx)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-all ${
                      selectedFeature === idx
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "hover:bg-accent text-muted-foreground"
                    }`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span className="text-xs font-medium">{feature.title}</span>
                  </button>
                )
              })}
            </nav>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-y-auto custom-scrollbar">
            <motion.div
              key={selectedFeature}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="max-w-3xl mx-auto p-6 space-y-6"
            >
              {/* Header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 rounded-xl bg-primary/10">
                  {React.createElement(FEATURE_DOCS[selectedFeature].icon, {
                    className: "w-6 h-6 text-primary"
                  })}
                </div>
                <div>
                  <h1 className="text-2xl font-bold">{FEATURE_DOCS[selectedFeature].title}</h1>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {FEATURE_DOCS[selectedFeature].description}
                  </p>
                </div>
              </div>

              {/* Sections */}
              <div className="space-y-4">
                {FEATURE_DOCS[selectedFeature].sections.map((section, idx) => (
                  <BentoCard key={idx} className="p-5">
                    <h3 className="text-lg font-semibold mb-2 text-foreground">
                      {section.heading}
                    </h3>
                    <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                      {section.content}
                    </div>
                  </BentoCard>
                ))}
              </div>

              {/* Footer tip */}
              <BentoCard className="p-5 bg-primary/5 border-primary/20">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1 text-sm">Need More Help?</h4>
                    <p className="text-xs text-muted-foreground">
                      Ask Rio directly in Operation! She can answer questions about features,
                      explain workflows, and guide you through any task.
                    </p>
                  </div>
                </div>
              </BentoCard>
            </motion.div>
          </main>
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
