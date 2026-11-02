
from pydantic import BaseModel, Field, ConfigDict


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="The customer's message",
    )

    conversation_id: int | None = Field(
        default=None,
        gt=0,
        description="Existing conversation ID; omit to start a new conversation",
    )

    session_token: str | None = Field(
        default=None,
        min_length=20,
        max_length=200,
        description="Anonymous browser session token",
    )


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reply: str
    assistant: str = "SupportIQ AI"
    conversation_id: int
