"""Pydantic schemas for chat endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    """Single message from the Vercel AI SDK useChat hook.

    AI SDK v6 may omit ``content`` and send ``parts`` instead.
    The validator derives ``content`` from text parts when missing.
    """
    model_config = {"extra": "allow"}
    role: str = Field(..., description="Message role: user | assistant | system | tool")
    content: Optional[str] = Field(None, description="Message text (derived from parts if absent)")
    id: Optional[str] = Field(None, description="AI SDK message ID")
    parts: Optional[List[Dict[str, Any]]] = Field(None, description="Structured message parts from AI SDK")
    tool_invocations: Optional[List[Dict[str, Any]]] = Field(None, alias="toolInvocations", description="Tool call data")

    @model_validator(mode="after")
    def _derive_content_from_parts(self) -> "ChatMessage":
        """If content is missing, build it from text parts."""
        if not self.content and self.parts:
            text_pieces = [
                p.get("text", "") for p in self.parts if p.get("type") == "text"
            ]
            self.content = "".join(text_pieces)
        if not self.content:
            self.content = ""
        return self


class WorkspaceChunk(BaseModel):
    """A single code chunk from a workspace file."""
    filePath: str = Field(..., description="Source file name")
    chunkName: str = Field(..., description="Function/class/block name")
    chunkKind: str = Field(..., description="Kind: function | class | interface | import | module")
    startLine: int = Field(..., description="Start line (1-based)")
    endLine: int = Field(..., description="End line (1-based)")
    content: str = Field(..., description="Chunk source code")


class WorkspaceFileTree(BaseModel):
    """Summary of a file's structure."""
    filePath: str
    tree: str


class WorkspaceContext(BaseModel):
    """Smart-chunked workspace context sent from the frontend."""
    file_trees: List[WorkspaceFileTree] = Field(default_factory=list)
    chunks: List[WorkspaceChunk] = Field(default_factory=list)
    total_tokens: int = Field(0)


class ChatRequest(BaseModel):
    """Body sent by the Vercel AI SDK useChat hook.

    Extra fields from the SDK (e.g. data, options) are preserved via extra="allow".
    Per-request model parameters override saved user settings when provided.
    """
    model_config = {"extra": "allow"}
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    thread_id: Optional[str] = Field(None, description="Existing thread ID to continue")
    mode: Optional[str] = Field("chat", description="Agent mode: chat | rag | web | sql")
    character: Optional[str] = Field("rio", description="Persona ID: rio")
    workspace_context: Optional[WorkspaceContext] = Field(None, description="Smart-chunked code context from workspace files")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Sampling temperature (0-2)")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Max tokens to generate")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Nucleus sampling (0-1)")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Frequency penalty (-2 to 2)")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Presence penalty (-2 to 2)")


class ThreadResponse(BaseModel):
    id: str
    title: Optional[str] = None
    status: str
    is_starred: bool = False
    is_pinned: bool = False
    created_at: str
    updated_at: str


class ThreadListResponse(BaseModel):
    success: bool = True
    threads: List[ThreadResponse]


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    character_id: Optional[str] = None


class MessageListResponse(BaseModel):
    success: bool = True
    messages: List[MessageResponse]


class MemoryResponse(BaseModel):
    key: str
    text: str
    memory_type: str = ""
    source: str = ""
    created_at: str = ""
    mode: str = ""


class MemoryListResponse(BaseModel):
    success: bool = True
    thread_id: str
    memories: List[MemoryResponse]


class ThreadPatchRequest(BaseModel):
    """Partial update for a thread."""
    title: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, description="active | archived")
    is_starred: Optional[bool] = None
    is_pinned: Optional[bool] = None
