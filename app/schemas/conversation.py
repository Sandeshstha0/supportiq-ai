from datetime import datetime

from pydantic import BaseModel


class StaffConversationSummary(BaseModel):
    id: int
    guest_session_id: int | None
    created_at: datetime
    latest_activity_at: datetime
    message_count: int
    preview: str | None
    has_customer_profile: bool


class StaffConversationPage(BaseModel):
    items: list[StaffConversationSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class StaffConversationMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class StaffConversationDetails(StaffConversationSummary):
    messages: list[StaffConversationMessage]
