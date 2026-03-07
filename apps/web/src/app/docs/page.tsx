"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Book, MessageSquare, Map, Database, FileText, StickyNote, Settings, Sparkles, Zap, Shield } from "lucide-react"
import { motion } from "framer-motion"
import { BentoCard } from "@/components/ui/bento-card"

const FEATURE_DOCS = [
  {
    title: "Operation (Chat)",
    icon: MessageSquare,
    description: "Your primary interface for interacting with Rio, your AI analyst companion.",
    sections: [
      {
        heading: "Starting a Conversation",
        content: "Click 'Operation' in the sidebar or press Cmd+2. Each conversation is a separate thread that maintains context."
      },
      {
        heading: "Chat Features",
        content: "• Streaming responses with real-time feedback\n• Mission extraction: Rio automatically detects tasks and creates missions\n• Affinity rewards: +1 affinity per message sent\n• Mood-aware responses: Rio's tone adapts to her current emotional state"
      },
      {
        heading: "Thread Management",
        content: "All conversations are saved. Use the thread selector in the sidebar to resume previous chats. Threads persist across sessions."
      }
    ]
  },
  {
    title: "Mission Control",
    icon: Map,
    description: "Task management system powered by AI-driven mission extraction.",
    sections: [
      {
        heading: "Creating Missions",
        content: "Missions are automatically extracted from your Operation chats when Rio detects actionable tasks. You can also manually create missions in the Mission view."
      },
      {
        heading: "Mission Structure",
        content: "• Title and description\n• Multiple steps with checkboxes\n• Scheduled start/end dates\n• Priority levels (low, medium, high, critical)\n• Status tracking (pending, in_progress, completed, cancelled)"
      },
      {
        heading: "Affinity Rewards",
        content: "Complete mission steps to earn +2 affinity per step. This strengthens your relationship with Rio."
      },
      {
        heading: "Calendar View",
        content: "Switch to calendar view to see your missions organized by date. Perfect for deadline tracking."
      }
    ]
  },
  {
    title: "Knowledge Base",
    icon: Database,
    description: "Upload and manage documents for context-aware AI assistance.",
    sections: [
      {
        heading: "Uploading Documents",
        content: "Drag and drop files into the Knowledge page. Supported formats include PDF, TXT, MD, DOCX, and more."
      },
      {
        heading: "Document Processing",
        content: "Uploaded documents are automatically:\n• Split into chunks for efficient retrieval\n• Embedded with vector representations\n• Indexed in Qdrant vector database\n• Made available to Rio for context-aware responses"
      },
      {
        heading: "Affinity Rewards",
        content: "+1 affinity per document uploaded. Building your knowledge base shows commitment to the partnership."
      },
      {
        heading: "Using Knowledge",
        content: "When chatting in Operation, Rio automatically searches your knowledge base for relevant context to provide more accurate answers."
      }
    ]
  },
  {
    title: "Notes System",
    icon: StickyNote,
    description: "Personal note-taking with collections and rich formatting.",
    sections: [
      {
        heading: "Creating Notes",
        content: "Click 'New Note' to create a standalone note. Notes support markdown formatting for rich text."
      },
      {
        heading: "Collections",
        content: "Organize notes into collections (folders). Create collections to group related notes by project, topic, or any category."
      },
      {
        heading: "Note Features",
        content: "• Markdown editor with live preview\n• Tags for categorization\n• Full-text search across all notes\n• Pinning important notes"
      }
    ]
  },
  {
    title: "Artifacts",
    icon: FileText,
    description: "View and manage AI-generated code, documents, and structured outputs.",
    sections: [
      {
        heading: "What are Artifacts?",
        content: "Artifacts are structured outputs created by Rio during conversations. They include code snippets, documents, JSON data, and other formatted content."
      },
      {
        heading: "Artifact Types",
        content: "• Code (Python, JavaScript, TypeScript, etc.)\n• Markdown documents\n• JSON/YAML data\n• HTML/CSS snippets\n• SQL queries"
      },
      {
        heading: "Using Artifacts",
        content: "All artifacts are automatically saved and can be viewed, copied, or downloaded from the Artifacts page."
      }
    ]
  },
  {
    title: "Emotional System",
    icon: Sparkles,
    description: "Rio's mood, affinity, and relationship progression.",
    sections: [
      {
        heading: "Mood States",
        content: "Rio has 6 mood states: Happy, Excited, Neutral, Sad, Frustrated, Tired. Her mood affects conversation tone and sticker display."
      },
      {
        heading: "Affinity System",
        content: "Affinity ranges from 0-1000 and increases through interaction:\n• +1 per chat message\n• +1 per document upload\n• +2 per mission step completed\n• +3 for 30+ minute sessions\n• -1 per day of absence (up to -10)"
      },
      {
        heading: "Relationship Tiers",
        content: "0-99: Stranger (formal, distant)\n100-299: Acquaintance (polite, professional)\n300-599: Friend (friendly, casual)\n600-899: Close Friend (warm, personal)\n900-1000: Bonded (deep connection, protective)"
      },
      {
        heading: "Tier Benefits",
        content: "Higher tiers unlock:\n• More expressive responses\n• Proactive suggestions and interventions\n• Personalized briefings\n• Unique stickers and animations"
      }
    ]
  },
  {
    title: "Settings & Preferences",
    icon: Settings,
    description: "Customize your experience and configure API keys.",
    sections: [
      {
        heading: "Model Settings",
        content: "Configure AI model parameters:\n• Temperature (creativity)\n• Max tokens (response length)\n• Top-p, frequency penalty, presence penalty\n• Choose between OpenAI and OpenRouter models"
      },
      {
        heading: "API Keys",
        content: "Securely store encrypted API keys:\n• OpenAI API key\n• OpenRouter API key\n• Tavily API key (web search)\n• Cohere API key (reranking)\n\nKeys are encrypted before storage and never exposed in responses."
      },
      {
        heading: "Notifications",
        content: "Control notification preferences:\n• Mission reminders\n• Chat alerts\n• System updates\n• Weekly summaries\n• Error alerts"
      },
      {
        heading: "Profile",
        content: "Update your username, email, bio, and study goals. These help Rio personalize her interactions."
      }
    ]
  },
  {
    title: "Keyboard Shortcuts",
    icon: Zap,
    description: "Navigate faster with keyboard shortcuts.",
    sections: [
      {
        heading: "Global Shortcuts",
        content: "• Cmd/Ctrl + K: Open command palette\n• Cmd/Ctrl + 1-6: Navigate to pages\n• Cmd/Ctrl + /: Toggle sidebar\n• Cmd/Ctrl + B: Toggle sidebar"
      },
      {
        heading: "Chat Shortcuts",
        content: "• Enter: Send message\n• Shift + Enter: New line\n• Escape: Clear input"
      }
    ]
  },
  {
    title: "Privacy & Security",
    icon: Shield,
    description: "How your data is protected.",
    sections: [
      {
        heading: "Data Storage",
        content: "All data is stored locally in your PostgreSQL database. Messages, missions, notes, and documents never leave your infrastructure."
      },
      {
        heading: "API Key Encryption",
        content: "API keys are encrypted using Fernet (AES-128 + HMAC) before database storage. Decryption only happens at runtime for API calls."
      },
      {
        heading: "Authentication",
        content: "JWT-based authentication with:\n• Access tokens (30-minute expiry)\n• Refresh tokens (7-day expiry)\n• Secure httpOnly cookies (when available)\n• CORS protection"
      }
    ]
  }
]

export default function DocsPage() {
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
