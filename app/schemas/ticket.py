from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=3000)
    customer_name: str | None = Field(default=None, max_length=150)
    customer_email: str | None = Field(default=None, max_length=255)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    subject: str
    description: str
    status: str
    customer_name: str | None
    customer_email: str | None
    created_at: datetime