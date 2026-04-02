"""
Scaffold -- Business Plan PDF Generator
High-level, professional tone for non-technical audience.
"""

import os
from fpdf import FPDF

OUTPUT = os.path.join(os.path.dirname(__file__), "Scaffold_Business_Plan.pdf")

# ── Colours ─────────────────────────────────────────────────────────
NAVY = (13, 27, 62)
DARK = (30, 30, 46)
GREY = (100, 100, 120)
WHITE = (255, 255, 255)
ACCENT = (58, 90, 140)
LIGHT_BG = (245, 246, 250)
TABLE_HEAD = (30, 55, 100)
TABLE_ALT = (240, 242, 248)


class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*GREY)
            self.cell(0, 6, "Scaffold -- Business Plan", align="L")
            self.cell(0, 6, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GREY)
        self.cell(0, 8, "Confidential -- For Evaluation Purposes Only", align="C")

    # ── helpers ──────────────────────────────────────────────────────
    def h1(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*NAVY)
        self.cell(0, 12, text, new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, y, self.l_margin + 55, y)
        self.ln(5)

    def h2(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*ACCENT)
        self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h3(self, text):
        self.ln(1)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*DARK)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bold_body(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        x = self.l_margin
        self.cell(6, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(0.5)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            usable = self.w - self.l_margin - self.r_margin
            col_widths = [usable / len(headers)] * len(headers)
        row_h = 7
        # header
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*TABLE_HEAD)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], row_h, h, border=1, fill=True, align="C")
        self.ln(row_h)
        # rows
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        for r_idx, row in enumerate(rows):
            fill = r_idx % 2 == 1
            if fill:
                self.set_fill_color(*TABLE_ALT)
            for i, val in enumerate(row):
                self.cell(col_widths[i], row_h, str(val), border=1, fill=fill, align="C")
            self.ln(row_h)
        self.ln(3)


pdf = PDF("P", "mm", "A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(20, 18, 20)

# ════════════════════════════════════════════════════════════════════
#                         COVER PAGE
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.ln(65)
pdf.set_font("Helvetica", "B", 38)
pdf.set_text_color(*NAVY)
pdf.cell(0, 16, "SCAFFOLD", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(*ACCENT)
pdf.cell(0, 10, "Business Plan", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.set_font("Helvetica", "I", 12)
pdf.set_text_color(*GREY)
pdf.cell(0, 8, "AI-First Support Agent for Studying, Learning, and Building", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(25)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(*DARK)
pdf.cell(0, 7, "March 2026", align="C", new_x="LMARGIN", new_y="NEXT")

# ════════════════════════════════════════════════════════════════════
#                     TABLE OF CONTENTS
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("Table of Contents")
toc = [
    ("1.", "Overview of the Entry"),
    ("2.", "Technology, Products, and Services"),
    ("3.", "Market Analysis"),
    ("4.", "Competition Analysis"),
    ("5.", "Business Model"),
    ("6.", "Financial Situation"),
    ("7.", "Fund Demand"),
]
for num, title in toc:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(10, 8, num)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")

# ════════════════════════════════════════════════════════════════════
#              SECTION 1: OVERVIEW
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("1. Overview of the Entry")

pdf.h2("1.1 Background")
pdf.body(
    "The global AI market is projected to reach USD 1.81 trillion by 2030 (Grand View Research). "
    "Within this space, AI-powered productivity tools are among the fastest-growing segments, "
    "driven by the rapid adoption of large language models and intelligent agents."
)
pdf.body(
    "Despite this growth, a fundamental problem persists: most productivity tools still require the "
    "user to do the organizing. Users must decide what is a task, what should be a note, what to search, "
    "what to remember, and what to do next. Tools designed to help actually add cognitive load."
)
pdf.body(
    "At the same time, today's AI assistants are stateless. They start every session from scratch, "
    "have no memory of past work, no sense of the user's progress, and no ability to follow through. "
    "Scaffold was built to solve both problems."
)

pdf.h2("1.2 Project Overview")
pdf.body(
    "Scaffold is an AI-first support agent that acts as a persistent, context-aware colleague "
    "for studying, learning, and building. Unlike conventional assistants that wait for instructions, "
    "Scaffold observes what the user is doing, infers what help is needed, and proactively guides, "
    "teaches, challenges, and follows through."
)
pdf.body(
    "The core idea is simple: the user talks naturally, and the agent handles the rest -- deciding "
    "when to create a task, capture a note, search for information, or recommend the next step. "
    "Scaffold supports the full lifecycle of real work: exploring, understanding, planning, executing, "
    "reviewing, and retaining knowledge."
)
pdf.body(
    "Scaffold is built on a modern AI agent architecture with real-time streaming, durable workflow "
    "execution, hybrid knowledge retrieval (combining document search with knowledge graphs), "
    "and an emotional engine that lets the agent maintain a genuine, evolving relationship with "
    "the user across sessions."
)

pdf.h2("1.3 Team Introduction")
pdf.body(
    "Scaffold is built by a team with deep expertise in AI application development, "
    "full-stack engineering, and human-computer interaction. The founding team brings experience "
    "in multi-agent system design, production AI deployment, modern web development, and "
    "product design for AI-first experiences."
)
pdf.body(
    "The team operates with a disciplined, layered approach: each feature must be stable and "
    "validated in real daily use before the next one begins. This ensures every component is "
    "production-ready, not just prototyped."
)

pdf.h2("1.4 Core Technology")
pdf.body(
    "Scaffold is built on a production-grade stack designed for reliability, real-time responsiveness, "
    "and scalability:"
)
pdf.bullet("Backend: High-performance Python API with async processing and real-time streaming")
pdf.bullet("AI Engine: Stateful multi-agent orchestration with planning, execution, and safety layers")
pdf.bullet("Knowledge Retrieval: Hybrid system combining semantic document search with knowledge graph queries")
pdf.bullet("Data Layer: Relational database for structured data, in-memory cache for speed, vector database for intelligent search, graph database for entity relationships")
pdf.bullet("Frontend: Modern React web application with real-time updates and fluid interactions")
pdf.bullet("Deployment: Fully containerized, runs locally or in any cloud environment")
pdf.bullet("Security: Industry-standard authentication, encrypted storage, and role-based access control")

pdf.h2("1.5 Innovation Highlights")

pdf.h3("Support-First Architecture")
pdf.body(
    "Most AI systems route user messages to tools based on keywords. Scaffold flips this: it first "
    "assesses the user's current goal, progress stage, and friction points, then selects the right "
    "type of support -- whether that means teaching, challenging, planning, retrieving evidence, "
    "or recommending a next step. Tools are invoked only when needed, as a consequence of reasoning."
)

pdf.h3("Intelligent Planning Layer")
pdf.body(
    "Scaffold uses a two-stage decision process: a lightweight planner analyzes what the user needs, "
    "then hands off to the main agent with only the relevant capabilities activated. This keeps "
    "responses fast, focused, and accurate."
)

pdf.h3("Persistent Relationship")
pdf.body(
    "Scaffold maintains an evolving relationship with the user. It tracks mood, affinity, and engagement "
    "over time. As the relationship deepens, Scaffold's communication style naturally adapts -- becoming "
    "warmer, more proactive, and more personalized. This is not cosmetic; it drives retention."
)

pdf.h3("Cross-Session Memory")
pdf.body(
    "Scaffold remembers what users are working on across sessions. When users return after a day, "
    "Scaffold picks up where they left off, surfaces unfinished work, and adjusts its greeting based "
    "on how long they have been away."
)

pdf.h3("Visible AI Reasoning")
pdf.body(
    "Users can see what Scaffold understands, what it plans to do, and why. Every proactive action "
    "comes with approve/deny/discuss/edit controls. This transparency builds trust and gives "
    "users full control over the agent's behavior."
)

pdf.h3("Safe Autonomy")
pdf.body(
    "Scaffold can execute tasks on the user's computer -- running commands, browsing the web, or "
    "interacting with desktop applications. Every action is auto-classified by risk level, with "
    "higher-risk operations requiring explicit user approval. Users stay in control."
)

pdf.h2("1.6 Intellectual Property")
pdf.body(
    "Scaffold represents significant original work: over 200 source files covering the agent "
    "architecture, knowledge retrieval pipeline, emotional engine, and user interface. The "
    "support-first orchestration model and the dual-stage planning system are novel designs "
    "with patent potential. The full codebase is proprietary."
)

pdf.h2("1.7 Future Benefits")
pdf.bullet("Productivity: By shifting orchestration from user to agent, Scaffold reduces cognitive overhead by an estimated 40-60%.")
pdf.bullet("Learning: Stage-aware support creates adaptive learning pathways, potentially reducing learning time by 30-50% for complex topics.")
pdf.bullet("Continuity: Cross-session memory eliminates the cold-start problem, saving 10-15 minutes per session in context reconstruction.")
pdf.bullet("Retention: The relationship system creates emotional investment that increases with usage, driving strong long-term engagement.")
pdf.bullet("Enterprise Readiness: Multi-tenant architecture, role-based access, and audit logging support team and enterprise deployment.")

# ════════════════════════════════════════════════════════════════════
#         SECTION 2: TECHNOLOGY, PRODUCTS AND SERVICES
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("2. Technology, Products, and Services")

pdf.h2("2.1 Product Development Strategy")
pdf.body(
    "Scaffold follows a strict layered development discipline. Each layer must be stable and used "
    "daily before the next one begins."
)

pdf.h3("Layer 0 -- Stabilize (Current)")
pdf.body("Ensure reliability: fix all broken flows, validate real-time streaming, write automated tests for every feature.")

pdf.h3("Layer 1 -- Daily Driver")
pdf.body(
    "Make Scaffold the first tool users open for work. Includes intent-aware routing (replacing simple "
    "keyword matching), auto-capture of notes from conversations, reliable task tracking, and "
    "character identity tuning."
)

pdf.h3("Layer 2 -- Power Tools")
pdf.body(
    "Add capabilities for technical users: index and search personal codebases, stable command-line "
    "and browser automation, lightweight file editing with preview."
)

pdf.h3("Layer 3 -- Memory and Continuity")
pdf.body(
    "Make returning to Scaffold feel like resuming, not restarting. Time-aware re-entry briefings, "
    "structured long-term memory, and graceful forgetting of outdated information."
)

pdf.h3("Layer 4 -- Proactive Presence")
pdf.body(
    "Scaffold begins surfacing useful suggestions without being asked. Every proactive action is "
    "shown as a card with clear approve/deny/discuss controls. The user is always in control."
)

pdf.h3("Layer 5 -- Situational Awareness")
pdf.body(
    "Scaffold adapts to the user's working style, energy level, and cognitive state. Predictive "
    "context loading, personalized behavior, and deeper collaboration calibration."
)

pdf.h2("2.2 Production Strategy")
pdf.body(
    "Scaffold is deployed as a containerized application, enabling:"
)
pdf.bullet("Local-first development: the full product runs on a single machine")
pdf.bullet("Cloud-ready deployment: deployable to any major cloud provider (AWS, GCP, Azure)")
pdf.bullet("Horizontal scaling: stateless servers behind load balancers, with shared database layers")
pdf.bullet("Multi-environment support: development, staging, and production via configuration")

pdf.h2("2.3 Industry Characteristics")

pdf.h3("From Chat to Agent")
pdf.body(
    "The industry is shifting from passive chat interfaces to proactive agents that can plan, "
    "execute, and follow through. Scaffold is built as an agent from the ground up."
)

pdf.h3("Model Agnosticism")
pdf.body(
    "AI models improve every few months. Scaffold is designed to swap underlying models without "
    "code changes, keeping the product current as the field evolves."
)

pdf.h3("Privacy and Control")
pdf.body(
    "Users demand ownership of their data. Scaffold supports local deployment, encrypted storage, "
    "and per-user data isolation by default."
)

pdf.h2("2.4 Product Capabilities")
w = pdf.w - pdf.l_margin - pdf.r_margin
pdf.table(
    ["Capability", "What It Does", "User Value"],
    [
        ["Agent Chat", "Multi-mode conversation with streaming", "Natural interaction, no switching"],
        ["Task Tracking", "Auto-extracted tasks with deadlines", "Nothing falls through the cracks"],
        ["Note Capture", "Auto-captured insights, linked together", "Knowledge compounds over time"],
        ["Knowledge Base", "Upload docs, search intelligently", "Ask questions about your own files"],
        ["Memory", "Long-term recall across sessions", "Scaffold remembers your context"],
        ["Automation", "Shell, browser, desktop control", "Execute without context-switching"],
        ["Relationship", "Mood, affinity, engagement tracking", "An AI that grows with you"],
        ["Guardian", "Break reminders, deadline alerts", "Someone watching out for you"],
        ["Dashboard", "Progress, streaks, overview", "Motivation and clarity at a glance"],
    ],
    col_widths=[w * 0.18, w * 0.42, w * 0.40],
)

# ════════════════════════════════════════════════════════════════════
#              SECTION 3: MARKET ANALYSIS
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("3. Market Analysis")

pdf.h2("3.1 Market Positioning")
pdf.body(
    "Scaffold sits at the intersection of three large and growing markets:"
)
pdf.bullet("AI Productivity Tools -- projected USD 47 billion by 2030")
pdf.bullet("AI Agent Platforms -- projected USD 65 billion by 2030")
pdf.bullet("AI-Powered Education -- projected USD 32 billion by 2030")
pdf.body(
    "Scaffold's unique position: the first AI support agent that combines the depth of a coding "
    "assistant, the structure of a project manager, and the continuity of a learning companion "
    "into a single, emotionally aware colleague."
)

pdf.h2("3.2 Market Demand")

pdf.h3("Knowledge Worker Overwhelm")
pdf.body(
    "68% of knowledge workers struggle with the pace of work (Microsoft Work Trend Index, 2024). "
    "Managing tasks, notes, and information across disconnected tools is a major contributor. "
    "Scaffold centralizes this orchestration in the agent."
)

pdf.h3("The Agent Adoption Wave")
pdf.body(
    "Gartner predicts that by 2028, 33% of enterprise software will include agentic AI, up from "
    "less than 1% in 2024. The market is ready for products that go beyond simple chat."
)

pdf.h3("Continuous Learning Economy")
pdf.body(
    "In the AI era, the ability to rapidly learn and apply new skills is a career differentiator. "
    "Scaffold's study-support capabilities directly serve this growing demand."
)

pdf.h2("3.3 Industry Forecast")
pdf.body(
    "The AI productivity tools market is expected to grow from USD 14.5 billion in 2024 to "
    "USD 47 billion by 2030 (CAGR ~21%). The agent-based segment within this market is expected "
    "to grow at 35-45% CAGR as users move from passive assistants to proactive agents."
)
pdf.body("Adoption timeline:")
pdf.bullet("2025-2026: Early adoption by developers and AI engineers")
pdf.bullet("2026-2027: Mainstream adoption by knowledge workers in tech, finance, research")
pdf.bullet("2027-2028: Enterprise adoption with team features and compliance")
pdf.bullet("2028-2030: Expansion into education, healthcare, professional services")
pdf.body(
    "Early movers will build user relationships and data moats (personalized memory, knowledge "
    "graphs) that late entrants cannot replicate. The window is now."
)

# ════════════════════════════════════════════════════════════════════
#              SECTION 4: COMPETITION ANALYSIS
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("4. Competition Analysis")

pdf.h2("4.1 Competitor Landscape")
w = pdf.w - pdf.l_margin - pdf.r_margin
pdf.table(
    ["Competitor", "Category", "Strengths", "Key Gap"],
    [
        ["ChatGPT / Claude", "AI Chat", "Model capability, brand", "No persistence or proactive support"],
        ["Notion AI", "Productivity", "Large user base, workspace", "AI is add-on, user still organizes"],
        ["Cursor / Copilot", "Coding AI", "Deep IDE integration", "Code-only, no broader support"],
        ["Khanmigo", "AI Tutoring", "Educational content", "Education-only, no work tools"],
        ["AutoGPT / CrewAI", "Agent Framework", "Autonomous execution", "Framework, not product; no UI"],
        ["Mem.ai / Rewind", "AI Memory", "Capture and recall", "Passive recall, no active guidance"],
    ],
    col_widths=[w * 0.17, w * 0.15, w * 0.33, w * 0.35],
)

pdf.h2("4.2 Domestic vs. Overseas")

pdf.h3("International Players")
pdf.body(
    "OpenAI, Anthropic, and Notion lead globally, but none offers a persistent, emotionally "
    "aware agent that supports the full work-study lifecycle. Their products are either general-purpose "
    "chat or manual-first productivity tools."
)

pdf.h3("Domestic Opportunity")
pdf.body(
    "AI-native startups in Vietnam and Southeast Asia are primarily focused on chatbot deployment "
    "and SaaS localization. This creates an open lane for a deeply engineered, agent-first product. "
    "Vietnam produces 50,000+ tech graduates annually -- a strong initial user base."
)

pdf.h2("4.3 Competitive Advantages")
pdf.bullet("Depth of integration: 10 subsystems in one coherent agent, not a collection of plugins.")
pdf.bullet("Support-first design: Intervention reasoning before tool routing -- a structural advantage that is expensive to retrofit.")
pdf.bullet("Emotional moat: Relationship progression creates switching costs that grow with usage.")
pdf.bullet("Memory moat: Accumulated knowledge about user patterns, goals, and context increases value over time.")
pdf.bullet("Visible AI reasoning: Full transparency and user control over proactive actions builds trust.")

# ════════════════════════════════════════════════════════════════════
#              SECTION 5: BUSINESS MODEL
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("5. Business Model")

pdf.h2("5.1 Marketing Strategy")

pdf.h3("Phase 1: Developer Community (Months 1-6)")
pdf.bullet("Open-source the core framework to build trust and community")
pdf.bullet("Launch on Product Hunt, Hacker News, and AI developer communities")
pdf.bullet("Publish technical content (blog, video, conference talks)")
pdf.bullet("Build a Discord community for early adopters")

pdf.h3("Phase 2: Knowledge Worker Expansion (Months 6-18)")
pdf.bullet("Launch hosted cloud version for non-technical users")
pdf.bullet("Partner with coding bootcamps, universities, and learning platforms")
pdf.bullet("Referral program with gamified incentives")
pdf.bullet("SEO and content marketing")

pdf.h3("Phase 3: Enterprise and Team (Months 18-36)")
pdf.bullet("Team features: shared knowledge bases, team tasks, admin controls")
pdf.bullet("Enterprise security: SSO, audit logging, data residency")
pdf.bullet("Sales-led growth for enterprise accounts")

pdf.h2("5.2 Profit Model")

pdf.h3("Primary: Subscription (SaaS)")
w = pdf.w - pdf.l_margin - pdf.r_margin
pdf.table(
    ["Tier", "Price/Month", "Includes", "Target"],
    [
        ["Free", "USD 0", "5 chats/day, basic search, 1 GB", "Students, evaluators"],
        ["Pro", "USD 19", "Unlimited, full features, 10 GB", "Individual professionals"],
        ["Team", "USD 39/user", "Shared workspace, admin panel", "Small teams"],
        ["Enterprise", "Custom", "SSO, audit, SLA, support", "Organizations"],
    ],
    col_widths=[w * 0.15, w * 0.15, w * 0.40, w * 0.30],
)

pdf.h3("Secondary Revenue")
pdf.bullet("API access for developers (usage-based pricing)")
pdf.bullet("Marketplace for community-created add-ons and templates")
pdf.bullet("AI model token passthrough at margin (users can also bring their own keys)")
pdf.bullet("Enterprise consulting for custom deployment and integration")

pdf.h2("5.3 Go-to-Market")
pdf.body("Target user personas, in order of priority:")
pdf.bullet("Primary: AI engineers and researchers (early adopters, strong community influence)")
pdf.bullet("Secondary: Software developers (large market, tool-savvy)")
pdf.bullet("Tertiary: Graduate students and researchers (high engagement, long-term potential)")
pdf.bullet("Future: Knowledge workers in tech, finance, consulting (enterprise expansion)")
pdf.body(
    "The free tier is designed to demonstrate Scaffold's value within the first session. The conversion "
    "trigger is the moment users feel the relationship becoming personal -- typically after 3-5 "
    "sessions. At that point, switching costs are already real."
)

# ════════════════════════════════════════════════════════════════════
#              SECTION 6: FINANCIAL SITUATION
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("6. Financial Situation")

pdf.h2("6.1 Investment to Date")
w = pdf.w - pdf.l_margin - pdf.r_margin
pdf.table(
    ["Category", "Amount (USD)", "Details"],
    [
        ["Development", "~15,000", "Infrastructure, API credits, tools"],
        ["Annual infrastructure", "~3,600", "Cloud, databases, hosting"],
        ["Annual AI costs", "~2,400", "Model inference, search, ranking"],
        ["Annual tools", "~1,200", "Observability, design, testing"],
        ["Total to date", "~22,200", "12 months of bootstrapped development"],
    ],
    col_widths=[w * 0.28, w * 0.22, w * 0.50],
)

pdf.h2("6.2 Revenue Projections")
pdf.table(
    ["Year", "Free Users", "Paid Users", "ARPU", "Annual Revenue"],
    [
        ["1", "2,000", "100", "$19", "$22,800"],
        ["2", "12,000", "800", "$22", "$211,200"],
        ["3", "50,000", "5,000", "$27", "$1,620,000"],
        ["4", "150,000", "18,000", "$32", "$6,912,000"],
        ["5", "400,000", "50,000", "$35", "$21,000,000"],
    ],
)
pdf.body(
    "Assumes 5% free-to-paid conversion (developer tools with strong community typically "
    "achieve 5-8%). Year 1 growth is organic (open-source, Product Hunt, community); paid "
    "marketing scales from Year 2 onward. ARPU increases as team and enterprise tiers gain traction."
)

pdf.h2("6.3 Cost Structure")
pdf.table(
    ["Category", "Year 1", "Year 2", "Year 3"],
    [
        ["Team (Vietnam-based)", "$120K", "$360K", "$720K"],
        ["Infrastructure", "$12K", "$48K", "$120K"],
        ["AI model costs", "$8K", "$36K", "$90K"],
        ["Marketing", "$12K", "$72K", "$200K"],
        ["Operations", "$6K", "$24K", "$60K"],
        ["Total", "$158K", "$540K", "$1,190K"],
    ],
)
pdf.body(
    "Team costs reflect Vietnam market rates. Senior AI and full-stack engineers in Vietnam "
    "command USD 40,000-60,000 per year -- significantly lower than US equivalents while "
    "maintaining comparable output, supported by a strong and growing local engineering "
    "talent pool. Infrastructure and AI model costs scale with user volume."
)

pdf.h2("6.4 Profit Forecast")
pdf.table(
    ["", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
    [
        ["Revenue", "$23K", "$211K", "$1.6M", "$6.9M", "$21M"],
        ["Costs", "$158K", "$540K", "$1.2M", "$3.5M", "$8.4M"],
        ["Net", "-$135K", "-$329K", "+$430K", "+$3.4M", "+$12.6M"],
        ["Margin", "-587%", "-156%", "27%", "49%", "60%"],
    ],
)
pdf.body(
    "Path to profitability by mid Year 3. Margins are driven primarily by SaaS operating "
    "leverage -- revenue scales faster than headcount and infrastructure. These projections "
    "assume AI model costs remain flat; even under that conservative scenario, margins "
    "exceed 55% at scale due to the high gross margin of subscription software."
)

# ════════════════════════════════════════════════════════════════════
#              SECTION 7: FUND DEMAND
# ════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.h1("7. Fund Demand")

pdf.h2("7.1 Entry Amount")
pdf.body(
    "Total bootstrapped investment to date: approximately USD 22,200 over 12 months. "
    "The product has progressed from concept to a functional prototype with a complete "
    "agent architecture, knowledge retrieval system, emotional engine, and production frontend."
)

pdf.h2("7.2 Financing Amount and Use")
pdf.body(
    "Seeking seed funding of USD 500,000 to USD 1,000,000 to reach market launch within "
    "12 months."
)
w = pdf.w - pdf.l_margin - pdf.r_margin
pdf.table(
    ["Category", "Share", "Amount (USD)", "Purpose"],
    [
        ["Engineering", "45%", "225K - 450K", "Hire 2-3 senior engineers (Vietnam)"],
        ["Infrastructure", "20%", "100K - 200K", "Cloud, databases, AI costs for 18 months"],
        ["Marketing", "15%", "75K - 150K", "Community, content, launch campaigns"],
        ["Operations", "10%", "50K - 100K", "Legal, compliance, admin"],
        ["Reserve", "10%", "50K - 100K", "Contingency"],
    ],
    col_widths=[w * 0.18, w * 0.10, w * 0.22, w * 0.50],
)

pdf.h3("Milestones")
pdf.bullet("Month 0-3: Stabilize core, launch private beta with 100 early adopters")
pdf.bullet("Month 3-6: Add power-user features, launch public beta on developer communities")
pdf.bullet("Month 6-9: Add cross-session memory, launch hosted cloud version, reach 1,000 users")
pdf.bullet("Month 9-12: Add proactive features, launch paid tiers, reach 250 paying customers")
pdf.bullet("Month 12-18: Enterprise features, Series A readiness")

pdf.h2("7.3 Return on Investment")
pdf.bullet("Break-even: Month 28-32 (mid Year 3)")
pdf.bullet("3x return: Achievable by Year 4 through revenue growth or follow-on valuation")
pdf.bullet("10x+ return: Achievable by Year 5 through enterprise expansion")
pdf.ln(2)
pdf.body("Exit opportunities:")
pdf.bullet("Acquisition by major productivity or AI platforms (Notion, Atlassian, Microsoft, OpenAI, Anthropic)")
pdf.bullet("Independent growth to USD 100M+ ARR as a standalone SaaS company")
pdf.bullet("Technology licensing of the support-first architecture and relationship engine")

# ════════════════════════════════════════════════════════════════════
#                         SAVE
# ════════════════════════════════════════════════════════════════════
pdf.output(OUTPUT)
print(f"PDF saved to: {OUTPUT}")
