import { MessageSquare, Map, Database, FileText, StickyNote, Settings, Sparkles, Zap, Shield, Link2 } from "lucide-react"

export const FEATURE_DOCS = [
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
      },
      {
        heading: "Note Links",
        content: "Link notes to other notes, documents, artifacts, and external media using Obsidian-style syntax. Links are auto-parsed when you save a note. See the 'Note Links' section in this manual for full syntax details."
      }
    ]
  },
  {
    title: "Note Links",
    icon: Link2,
    description: "Obsidian-style linking between notes, documents, artifacts, and media.",
    sections: [
      {
        heading: "What are Note Links?",
        content: "Note Links let you connect your notes to other notes, documents, artifacts, videos, and URLs using a simple syntax embedded in your note content. When you save a note, the system automatically parses link syntax and creates trackable link records."
      },
      {
        heading: "Link Syntax",
        content: "Embed links directly in your note content using these patterns:\n\n• [[Note Title]] — link to another note by its title\n• [[note:uuid]] — link to a note by its ID\n• [[doc:uuid|Display Name]] — link to a document\n• [[artifact:uuid|Display Name]] — link to an artifact\n• [label](url) — standard markdown link to any URL\n• [label](url?t=120) — video link with timestamp (seconds)\n• [label](url#page=3) — PDF/slide link with page number"
      },
      {
        heading: "Auto-Sync",
        content: "Links are automatically managed:\n• When you create or update a note, the system scans the content for link syntax\n• New links are created as NoteLink records\n• Removed links are cleaned up automatically\n• No manual link management needed — just write the syntax in your notes"
      },
      {
        heading: "Backlinks",
        content: "Discover which notes link TO a specific note. Backlinks help you navigate your knowledge graph in reverse — see all the places a note is referenced."
      },
      {
        heading: "Graph Visualization",
        content: "View your entire note network as an interactive graph. Nodes represent notes, documents, and artifacts. Edges represent the links between them. Use the graph to discover connections and navigate your knowledge base."
      },
      {
        heading: "Media Metadata",
        content: "Links to media (videos, PDFs) can carry extra metadata:\n• Video timestamps: [lecture](https://youtube.com/watch?v=xxx?t=120) stores the start time\n• PDF pages: [paper](https://example.com/paper.pdf#page=3) stores the page number\n• This metadata is preserved so you can jump directly to the right spot"
      },
      {
        heading: "API Endpoints",
        content: "• POST /note-links — create a link manually\n• POST /note-links/bulk — bulk create links\n• GET /note-links — list links (filter by note_id, target_type)\n• GET /note-links/graph — get graph visualization data\n• GET /note-links/backlinks/{note_id} — get backlinks\n• PATCH /note-links/{link_id} — update a link\n• DELETE /note-links/{link_id} — delete a link"
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
