"""
Memory Worker - Handles Explicit Memory Operations.

This worker handles user requests related to long-term memory:
- "Remember that..." - Store explicit facts
- "What do you know about me?" - List stored memories
- "Forget that..." - Delete specific memories

The Memory Worker complements the automatic memory system (Phase 1 & 2)
by giving users explicit control over what the agent remembers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from langchain_core.messages import HumanMessage

from application.workflows.workers.base import BaseWorker
from application.workflows.state import AgentState, WorkerResult, WorkerType
from utils.log import log_debug, log_info, log_warning

if TYPE_CHECKING:
    from core.settings import AgentConfig


# Extend WorkerType for memory (we'll add this dynamically)
# For now, we'll use a string identifier


class MemoryAction:
    """Types of memory operations."""
    STORE = "store"      # Remember something
    RECALL = "recall"    # List/search memories
    FORGET = "forget"    # Delete memories


MEMORY_ANALYSIS_PROMPT = """Analyze the user's request about memory and determine the action.

User's message: {message}

Determine:
1. ACTION: Is the user asking to STORE something (remember), RECALL something (what do you know), or FORGET something?
2. CONTENT: What specific fact or topic should be stored/recalled/forgotten?

Output format (exactly):
ACTION: [STORE|RECALL|FORGET]
CONTENT: [The specific fact to store, or the topic to recall/forget]

Examples:
- "Remember that I work at Google" → ACTION: STORE, CONTENT: User works at Google
- "What do you know about me?" → ACTION: RECALL, CONTENT: general user information
- "Forget my email address" → ACTION: FORGET, CONTENT: email address

Now analyze:"""


class MemoryWorker(BaseWorker):
    """
    Worker for explicit memory operations.
    
    Handles:
    - Storing user-specified facts ("Remember that...")
    - Recalling stored memories ("What do you know about me?")
    - Deleting memories ("Forget that...")
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.MEMORY
    
    @property
    def name(self) -> str:
        return "Memory Worker"
    
    @property
    def description(self) -> str:
        return "Manages long-term memory: stores, recalls, and forgets user information."
    
    @property
    def system_prompt(self) -> str:
        return """You are the Memory Worker, responsible for managing the user's long-term memory.

Your capabilities:
1. STORE: Save facts the user explicitly asks you to remember
2. RECALL: Retrieve and list what you know about the user
3. FORGET: Remove specific memories when asked

Be precise about what you're storing or retrieving. Confirm actions clearly."""

    def _execute(self, state: AgentState) -> WorkerResult:
        """Execute the memory operation."""
        question = state.get("original_question", "")
        user_id = state.get("user_id")
        
        if not user_id:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Cannot manage memories without user identification.",
                error="No user_id in state",
            )
        
        # Analyze the request
        action, content = self._analyze_request(question)
        log_info(f"Memory action: {action}, content: {content[:100] if content else 'None'}")
        
        if action == MemoryAction.STORE:
            return self._handle_store(user_id, content)
        elif action == MemoryAction.RECALL:
            return self._handle_recall(user_id, content)
        elif action == MemoryAction.FORGET:
            return self._handle_forget(user_id, content)
        else:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Could not determine memory action from your request.",
                error="Unknown action",
            )
    
    def _analyze_request(self, message: str) -> tuple[str, str]:
        """Analyze the user's message to determine action and content."""
        message_lower = message.lower().strip()
        
        # Quick pattern matching for common phrases
        store_patterns = [
            r"remember\s+that\s+(.+)",
            r"don'?t\s+forget\s+that\s+(.+)",
            r"keep\s+in\s+mind\s+that\s+(.+)",
            r"note\s+that\s+(.+)",
            r"save\s+(?:this|that)\s*:?\s*(.+)",
        ]
        
        recall_patterns = [
            r"what\s+do\s+you\s+(?:know|remember)\s+about\s+(.+)",
            r"what\s+have\s+you\s+(?:stored|saved|remembered)",
            r"list\s+(?:my\s+)?memories",
            r"show\s+(?:me\s+)?what\s+you\s+(?:know|remember)",
            r"recall\s+(.+)",
        ]
        
        forget_patterns = [
            r"forget\s+(?:that\s+)?(.+)",
            r"delete\s+(?:the\s+)?memory\s+(?:about\s+)?(.+)",
            r"remove\s+(?:the\s+)?(?:fact|memory)\s+(?:about\s+)?(.+)",
            r"don'?t\s+remember\s+(.+)",
        ]
        
        # Try store patterns
        for pattern in store_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                content = match.group(1).strip() if match.groups() else message
                return MemoryAction.STORE, content
        
        # Try recall patterns
        for pattern in recall_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                content = match.group(1).strip() if match.groups() else "general"
                return MemoryAction.RECALL, content
        
        # Try forget patterns
        for pattern in forget_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                content = match.group(1).strip() if match.groups() else ""
                return MemoryAction.FORGET, content
        
        # Fallback: use LLM to analyze
        return self._llm_analyze(message)
    
    def _llm_analyze(self, message: str) -> tuple[str, str]:
        """Use LLM to analyze the memory request."""
        try:
            prompt = MEMORY_ANALYSIS_PROMPT.format(message=message)
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", str(response))
            
            # Parse response
            action_match = re.search(r"ACTION:\s*(\w+)", content, re.IGNORECASE)
            content_match = re.search(r"CONTENT:\s*(.+)", content, re.IGNORECASE)
            
            action = action_match.group(1).upper() if action_match else "RECALL"
            extracted_content = content_match.group(1).strip() if content_match else message
            
            if action == "STORE":
                return MemoryAction.STORE, extracted_content
            elif action == "FORGET":
                return MemoryAction.FORGET, extracted_content
            else:
                return MemoryAction.RECALL, extracted_content
                
        except Exception as e:
            log_warning(f"LLM analysis failed: {e}")
            return MemoryAction.RECALL, "general"
    
    def _handle_store(self, user_id: str, content: str) -> WorkerResult:
        """Store a fact in long-term memory."""
        from application.workflows.memory_store import (
            get_memory_store,
            store_memory,
        )
        from uuid import uuid4
        
        if not content or len(content) < 3:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Please specify what you want me to remember.",
                error="Empty content",
            )
        
        try:
            store = get_memory_store()
            memory_key = f"explicit_{uuid4().hex[:8]}"
            
            store_memory(
                store,
                user_id=user_id,
                memory_key=memory_key,
                text=content,
                memory_type="semantic",
                metadata={
                    "source": "user_explicit",
                    "explicit": True,
                },
            )
            
            # Close the store connection
            if hasattr(store, '__exit__'):
                store.__exit__(None, None, None)
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=f"✓ I'll remember: \"{content}\"",
            )
            
        except Exception as e:
            log_warning(f"Failed to store memory: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content=f"Sorry, I couldn't save that memory: {str(e)}",
                error=str(e),
            )

    def _handle_recall(self, user_id: str, topic: str) -> WorkerResult:
        """Recall stored memories."""
        from application.workflows.memory_store import (
            get_memory_store,
            search_memories,
            format_memories_for_prompt,
        )
        
        try:
            store = get_memory_store()
            
            # Search for relevant memories
            memories = search_memories(
                store,
                user_id=user_id,
                query=topic if topic != "general" else "user preferences information facts",
                limit=10,
            )
            
            # Close the store connection
            if hasattr(store, '__exit__'):
                store.__exit__(None, None, None)
            
            if not memories:
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content="I don't have any stored memories about you yet. You can tell me things to remember by saying 'Remember that...'",
                )
            
            # Format memories for display
            parts = ["Here's what I remember about you:\n"]
            for i, mem in enumerate(memories, 1):
                text = mem.get("text", "")
                mem_type = mem.get("memory_type", "unknown")
                score = mem.get("score")
                
                # Mark explicit memories
                is_explicit = mem.get("metadata", {}).get("explicit", False)
                marker = "📌" if is_explicit else "💭"
                
                if score is not None:
                    parts.append(f"{i}. {marker} {text} (relevance: {score:.0%})")
                else:
                    parts.append(f"{i}. {marker} {text}")
            
            parts.append("\n📌 = explicitly saved | 💭 = learned from conversation")
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content="\n".join(parts),
            )
            
        except Exception as e:
            log_warning(f"Failed to recall memories: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content=f"Sorry, I couldn't retrieve memories: {str(e)}",
                error=str(e),
            )

    def _handle_forget(self, user_id: str, topic: str) -> WorkerResult:
        """Delete memories matching the topic."""
        from application.workflows.memory_store import (
            get_memory_store,
            search_memories,
            delete_memory,
        )
        
        if not topic or len(topic) < 3:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Please specify what you want me to forget.",
                error="Empty topic",
            )
        
        try:
            store = get_memory_store()
            
            # Find matching memories
            memories = search_memories(
                store,
                user_id=user_id,
                query=topic,
                limit=5,
            )
            
            if not memories:
                # Close the store connection
                if hasattr(store, '__exit__'):
                    store.__exit__(None, None, None)
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content=f"I don't have any memories about '{topic}' to forget.",
                )
            
            # Delete matching memories
            deleted_count = 0
            for mem in memories:
                key = mem.get("key")
                if key:
                    if delete_memory(store, user_id=user_id, memory_key=key):
                        deleted_count += 1
            
            # Close the store connection
            if hasattr(store, '__exit__'):
                store.__exit__(None, None, None)
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=f"✓ Forgotten {deleted_count} memory(ies) related to '{topic}'.",
            )
            
        except Exception as e:
            log_warning(f"Failed to forget memories: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content=f"Sorry, I couldn't forget that: {str(e)}",
                error=str(e),
            )


def create_memory_worker(config: Optional["AgentConfig"] = None) -> MemoryWorker:
    """Factory function to create a MemoryWorker."""
    return MemoryWorker(config=config)
