"""
models.py
---------
Pydantic models used as the API contract between the frontend and backend.
Keeping them here makes the contract easy to find and change.
"""

from typing import List
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in the conversation (either user or assistant)."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="The message text")


class ChatRequest(BaseModel):
    """
    What the frontend sends on every /chat call.

    - message : the user's latest question
    - history : all previous turns so the model has conversation context
    """
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = Field(default_factory=list)


class Source(BaseModel):
    """Metadata for a retrieved Amenify page used to generate the answer."""
    url: str
    title: str


class ChatResponse(BaseModel):
    """What the backend returns to the frontend."""
    answer: str
    sources: List[Source] = Field(default_factory=list)
