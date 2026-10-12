"""Schemas for the student chatbot (docs/Phases.md — general-purpose Q&A)."""
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One turn in a conversation. Only role + content are client-supplied."""

    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    """A chatbot question with optional short conversation history.

    History is capped so prompts (and cost) stay bounded: last 10 turns,
    2000 chars each. The server never persists chat content.
    """

    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    reply: str
    model: str
