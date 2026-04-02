# AI-First Support Agent

## North Star

Project Rio is an AI-first product that acts like a supportive agent for:

- studying
- learning
- working

The agent is the product.

The user should not need to manually structure everything first into tasks, notes,
folders, or workflows before getting useful help.

The system should:

- notice what the user is trying to do
- infer what kind of help is needed next
- proactively guide, challenge, teach, structure, and follow through
- create persistent structure only when it is genuinely useful

`Mission`, `Note`, `RAG`, `SQL`, `WebSearch`, and similar systems are support
subsystems under the agent. They are not the center of the product.


## Product Thesis

Most productivity and knowledge apps make the user do the orchestration:

- decide what should be a task
- decide what should be a note
- decide what to search
- decide what should be remembered
- decide what the next step is

Rio flips that model:

- the user talks naturally
- the agent models the situation
- the agent chooses the right intervention
- the agent uses structure as a consequence of reasoning


## Non-Goals

This product is not trying to make:

- tools the main product
- a generic chatbot with many tools
- a fully autonomous system that acts without boundaries
- a passive assistant that only reacts to explicit commands


## Core Product Model

Rio should support the full lifecycle of real work:

1. `explore`
2. `understand`
3. `plan`
4. `execute`
5. `review`
6. `retain`

The orchestrator should ask:

- What is the user actually trying to achieve?
- What stage are they in?
- What is getting in the way?
- What intervention will help most right now?
- Should this remain conversational, or should it become persistent structure?


## Architecture Overview

### Layer 1: Support Orchestrator

The current supervisor is mostly a worker router.

Rio should instead use a support orchestrator that owns:

- user-stage assessment
- progress-friction assessment
- intervention selection
- action authority
- follow-through decisions

Top-level question:

- not "Which worker should run?"
- but "What does the user need next to make progress?"

### Layer 2: Capability Workers

Workers remain narrow and deterministic:

- `Mission`: commitments, steps, deadlines, progress
- `Note`: durable understanding and knowledge capture
- `RAG`: grounded internal retrieval
- `WebSearch`: current external retrieval
- `SQL`: structured application data
- `Memory`: long-term user profile and repeated patterns
- `OSControl`: high-trust operational actions

### Layer 3: Product Surfaces

Frontend and stream protocol should present support behavior, not only tool activity.

The main shell should show:

- what Rio thinks the user is doing
- what Rio thinks is getting in the way
- what Rio chose to do next
- what Rio recommends next


## Workflow Graph

Proposed top-level graph:

1. `input_guardrail`
2. `observe_context`
3. `assess_support_state`
4. `decide_intervention`
5. `delegate_capabilities`
6. `reflect_outcome`
7. `commit_support_state`
8. `synthesize_response`
9. `output_guardrail`

### Node Responsibilities

#### `observe_context`

Collects:

- latest user request
- recent thread history
- relevant missions
- relevant notes
- memory hints
- gathered context from prior workers

It should build a compact situation snapshot, not decide actions yet.

#### `assess_support_state`

Produces structured assessment:

- inferred goal
- user stage
- what Rio thinks is getting in the way
- knowledge gap
- urgency
- confidence to act
- whether something should be revisited later

#### `decide_intervention`

Chooses one primary intervention type and optional secondary ones.

Examples:

- teach
- clarify
- challenge
- break_down
- plan
- retrieve_evidence
- draft_structure
- commit_structure
- review_progress
- summarize_learning
- recommend_next_step

#### `delegate_capabilities`

Runs workers only when the chosen intervention requires them.

Examples:

- `teach` may use `RAG`
- `retrieve_evidence` may use `RAG` or `WebSearch`
- `draft_structure` may produce a mission draft or note draft
- `commit_structure` may invoke Mission or Note mutations
- `review_progress` may use Mission plus Memory

#### `reflect_outcome`

After tool usage, reassess:

- did the intervention succeed
- did the user become clearer
- should a note be captured
- should a mission be created to help the user follow through
- what is the best next step now

#### `commit_support_state`

Persists support-layer state needed across turns:

- goal continuity
- stage continuity
- things Rio wants to revisit later
- recommended next step

#### `synthesize_response`

Builds the final answer in a supportive, agent-led voice based on:

- support assessment
- intervention choice
- worker results
- next-step recommendation


## New Support State Schema

Extend `AgentState` with a support-layer section. Suggested fields:

```python
support_state: {
    "primary_goal": str | None,
    "goal_candidates": list[str],
    "current_stage": Literal[
        "explore", "understand", "plan", "execute", "review", "retain"
    ] | None,
    "current_friction": str | None,
    "secondary_frictions": list[str],
    "knowledge_gap": str | None,
    "execution_risk": Literal["low", "medium", "high"] | None,
    "initiative_level": Literal["low", "balanced", "high"],
    "confidence_to_act": float | None,
    "recommended_next_step": str | None,
    "revisit_later": list[str],
    "support_summary": str | None,
}
```

Also add explicit intervention state:

```python
current_intervention: Literal[
    "teach",
    "clarify",
    "challenge",
    "break_down",
    "plan",
    "retrieve_evidence",
    "draft_structure",
    "commit_structure",
    "review_progress",
    "summarize_learning",
    "recommend_next_step",
] | None

intervention_reasoning: str | None
```


## Authority Model

To make Rio more proactive without becoming reckless, actions should be grouped by authority:

- `talk`: no writes
- `draft`: Rio can propose notes and missions automatically
- `act`: Rio can create reversible structure automatically
- `confirm`: Rio must ask before destructive, expensive, or risky actions

This gives Rio initiative while keeping trust intact.

Suggested uses:

- create note draft: `draft`
- create mission: `act`
- edit mission status: `act`
- delete mission or note: `confirm`
- run OS actions: `confirm` or role-gated


## Mission and Note

### Mission

Mission should remain a commitment and execution-tracking subsystem.

Mission should be used when the user has moved into or near execution:

- actionable commitment
- multi-step work
- deadlines
- recurring follow-through

Mission should not be the default output of every conversation.

### Note

Note should capture durable understanding:

- concepts
- summaries
- takeaways
- links between ideas
- learning artifacts

Note should be used when the interaction produced knowledge worth retaining.

### Shared Principle

Mission and Note are outputs of support reasoning, not the center of the product.


## Intervention-to-Worker Mapping

Suggested first-pass mapping:

- `teach`
  - optional workers: `RAG`, `WebSearch`
- `clarify`
  - usually no worker
- `challenge`
  - usually no worker
- `break_down`
  - optional worker: `Mission` draft only
- `plan`
  - optional workers: `Planning`, `Mission` draft
- `retrieve_evidence`
  - workers: `RAG`, `WebSearch`, `SQL`
- `draft_structure`
  - workers: `Mission`, `Note`
- `commit_structure`
  - workers: `Mission`, `Note`
- `review_progress`
  - workers: `Mission`, `Memory`, `Note`
- `summarize_learning`
  - workers: `Note`, `RAG`
- `recommend_next_step`
  - optional worker: `Mission`


## Streaming Event Contract

The current stream already carries worker and supervisor events.

The stream should preserve those events and add support-layer events.

New events:

- `data-support-assessment`
- `data-stage-assessment`
- `data-intervention-decision`
- `data-next-step`
- `data-draft-mission`
- `data-draft-note`
- `data-revisit-later`
- `data-pending-action`

Example payloads:

```json
{
  "type": "data-stage-assessment",
  "data": {
    "current_stage": "understand",
    "primary_goal": "understand diffusion models well enough to explain them simply",
    "current_friction": "Conceptual confusion around noise prediction"
  }
}
```

```json
{
  "type": "data-intervention-decision",
  "data": {
    "intervention": "teach",
    "reasoning": "User is confused and needs explanation before planning",
    "confidence": 0.89
  }
}
```

```json
{
  "type": "data-next-step",
  "data": {
    "recommended_next_step": "Explain the denoising loop in one paragraph, then test with a toy example"
  }
}
```

```json
{
  "type": "data-pending-action",
  "data": {
    "title": "Create a mission for exam prep",
    "why": "The user has repeated this goal and it now has clear executable steps",
    "impact": "Creates 1 mission with 4 steps",
    "state": "waiting_for_user",
    "controls": ["approve", "deny", "edit", "discuss"]
  }
}
```


## Frontend Product Changes

### Frontend Principle

If Rio is going to act more aggressively, the frontend cannot feel like hidden automation.

The user should always be able to:

- see what Rio noticed
- see what Rio wants to do
- see why Rio wants to do it
- approve, deny, discuss, or modify it
- review what already happened

The UI should make Rio's intent visible and controllable.

### Main Shell

The current shell in `MissionControl` is effectively the main agent surface.

Rio should keep the thread-based shell but evolve its meaning:

- show support state, not just mission context
- show intervention and next-step guidance
- keep existing chat flow and thread continuity

Longer term, the component name should move away from mission-first framing.

### Main Support Panel

The main support panel should prioritize plain-language product labels:

- `What Rio understands`
- `What Rio thinks you need next`
- `What Rio wants to do`
- `Recent actions`

These are better product labels than internal orchestration terms.

### Sidebar

Current sidebar already handles:

- supervisor decisions
- worker results
- note and mission events
- workspace references

The support sidebar should add:

- current stage
- what Rio thinks is getting in the way
- intervention chosen
- recommended next step
- things Rio wants to revisit later

The sidebar becomes Rio's support model of the situation, not just a tool log.

### Pending Action Cards

Every proactive action should appear as a clear action card.

Each card should show:

- `Action`
- `Why`
- `Impact`
- `State`

Each card should allow:

- `Approve`
- `Deny`
- `Discuss`
- `Edit`

Example:

- Action: `Create a mission for exam prep`
- Why: `You repeated this goal several times and it now has clear executable steps`
- Impact: `Creates 1 mission with 4 steps`
- State: `Waiting for you`

### Action States

Use a visible lifecycle for proactive actions:

- `Observed`
- `Suggested`
- `Waiting for you`
- `Running`
- `Done`
- `Dismissed`

This is clearer than exposing workflow-engine terminology.

### Control Model

Not every action should behave the same way.

There should be four action modes:

- `Suggestion only`
- `Auto-draft`
- `Auto-act`
- `Approval required`

This should map to Rio's initiative settings and action authority.

### Discuss Flow

`Discuss` should not cancel the action by default.

It should convert the pending action back into collaborative conversation, for example:

- `Don't create it yet`
- `Make it narrower`
- `Use a note instead`
- `Wait until tomorrow`

That makes Rio feel collaborative instead of rigid.

### Avoid Internal Product Language

Do not make the main UI feel like a workflow debugger.

Avoid using worker and orchestration terms as the main product language when a simpler
user-facing label exists.

Examples:

- instead of `blocker diagnosis`, use `What Rio thinks is getting in the way`
- instead of `follow-up markers`, use `Things Rio wants to revisit later`
- instead of showing only worker logs, show recommended actions and outcomes

### Mission UI

Mission page stays useful, but as a subsystem page:

- track commitments
- review execution
- update progress
- inspect deadlines and steps

It should no longer imply that the product is mission-first.


## Backend Changes by File

### `src/workflows/state.py`

Add:

- support state fields
- intervention enums
- authority mode

### `src/workflows/supervisor.py`

Refactor into support orchestrator responsibilities:

- detect user stage
- assess what Rio thinks is getting in the way
- choose intervention
- select worker only when needed

### `src/workflows/graph.py`

Add new nodes:

- `observe_context`
- `assess_support_state`
- `decide_intervention`
- `reflect_outcome`
- `commit_support_state`

### `src/workflows/executor.py`

Emit new support-layer events and keep existing worker events stable.

### `src/services/agent_service.py`

Minimal surface changes if the underlying stream contract remains iterator-based.

### `src/routers/chat.py`

Extend SSE output with support-state events.

### `apps/web/src/features/chat/lib/chat-transport.ts`

Add dispatch handlers for:

- support assessment
- intervention decision
- next step
- revisit later
- pending actions
- draft structures

### `apps/web/src/features/chat/store.ts`

Add support-oriented state:

- current stage
- current friction
- intervention
- next step
- revisit later
- pending actions
- recent actions

### `apps/web/src/features/mission/components/MissionControl.tsx`

Keep the chat shell behavior, but render support state and pending actions in HUD/sidebar.


## Migration Strategy

### Phase 1: Add Support Layer Without Breaking Existing Workers

Goal:

- keep worker execution intact
- add support assessment and intervention selection before routing

Deliverables:

- new support fields in `AgentState`
- support assessment node
- intervention decision node
- new stream events

### Phase 2: Make Supervisor Stage-Aware

Goal:

- route by user need, not keyword-only worker detection

Deliverables:

- stage inference
- friction inference
- intervention selection logic

### Phase 3: Add Draft vs Commit Structure

Goal:

- avoid spammy persistence
- allow Rio to be proactive without overcommitting

Deliverables:

- draft mission flow
- draft note flow
- commit rules and authority checks

### Phase 4: Frontend Support Surface

Goal:

- make the UI visibly AI-first and user-controlled

Deliverables:

- support-state sidebar panels
- stage/intervention indicators
- next-step cards
- pending action cards with approve, deny, discuss, and edit controls

### Phase 5: Follow-Through Engine

Goal:

- make Rio feel persistent across time

Deliverables:

- revisit-later signals
- resurfacing unfinished important work
- thread-to-thread continuity


## First Implementation Slice

The safest first slice is:

1. extend `AgentState` with support fields
2. add `assess_support_state` node
3. add `decide_intervention` node
4. emit `data-stage-assessment`, `data-intervention-decision`, and `data-next-step`
5. update frontend sidebar store to render those three signals

This gives visible AI-first behavior without requiring worker rewrites first.


## Evaluation Criteria

The product should be evaluated on support quality, not only tool correctness.

Track:

- did Rio identify the right user stage
- did Rio choose the right intervention
- did Rio create structure only when useful
- did Rio recommend a strong next step
- did Rio avoid over-helping or under-helping
- did Rio help the user move forward
- did the user understand and control proactive actions

User-level success signals:

- "I do not need to manually structure everything first."
- "Rio knows what I need next."
- "Rio helps me think, learn, and execute."
- "Rio pushes when needed."
- "I can still see and control what Rio wants to do."


## Summary

This is not a worker expansion.

This is a shift in product control:

- from worker-first to support-first
- from tool routing to intervention selection
- from passive response to proactive guidance
- from structure-first to reasoning-first
- from hidden automation to visible and controllable agent action

That is the architecture needed for an AI-first supportive agent for studying,
working, and learning.
