from datetime import datetime

from pydantic import BaseModel


class CustomerStats(BaseModel):
    total_guest_sessions: int
    sessions_with_orders: int
    sessions_with_tickets: int


class CustomerDirectoryItem(BaseModel):
    customer_id: int
    identity_type: str = "guest_session"
    name: str | None
    phone: str | None
    email: str | None
    location: str | None
    first_seen: datetime
    order_count: int
    ticket_count: int
    conversation_count: int


class CustomerDirectoryResponse(BaseModel):
    items: list[CustomerDirectoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: CustomerStats
    identity_note: str


class CustomerOrderHistory(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    customer_email: str | None
    delivery_location: str
    ward_number: int
    total_amount: float
    status: str
    created_at: datetime


class CustomerTicketHistory(BaseModel):
    id: int
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    category: str
    subject: str
    status: str
    created_at: datetime


class CustomerConversationMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class CustomerConversationHistory(BaseModel):
    id: int
    created_at: datetime
    message_count: int
    messages: list[CustomerConversationMessage]


class CustomerActivity(BaseModel):
    type: str
    record_id: int
    occurred_at: datetime
    summary: str


class CustomerDetails(CustomerDirectoryItem):
    expires_at: datetime
    orders: list[CustomerOrderHistory]
    tickets: list[CustomerTicketHistory]
    conversations: list[CustomerConversationHistory]
    activity: list[CustomerActivity]
