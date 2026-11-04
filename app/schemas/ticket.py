
from datetime import datetime

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TicketDecisionUpdate(BaseModel):
    decision: str = Field(
        min_length=5,
        max_length=3000,
    )

    status: Literal[
        "open",
        "in_progress",
        "resolved",
        "closed",
    ]

    @field_validator("decision")
    @classmethod
    def decision_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Decision/update must contain at least 5 characters.")
        return value

class TicketCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=3000)

    customer_name: str | None = Field(default=None, max_length=150)
    customer_email: str | None = Field(default=None, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_contact_information(self):
        email = self.customer_email
        phone = self.customer_phone

        if not (email and email.strip()) and not (phone and phone.strip()):
            raise ValueError(
                "Please provide at least an email address or phone number."
            )

        if email:
            self.customer_email = email.strip()

        if phone:
            self.customer_phone = phone.strip()

        return self


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    guest_session_id: int | None
    category: str
    subject: str
    description: str
    status: str
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    created_at: datetime


class TicketStaffResponse(TicketResponse):
    decision: str | None
    updated_at: datetime | None


class TicketListResponse(BaseModel):
    items: list[TicketStaffResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
