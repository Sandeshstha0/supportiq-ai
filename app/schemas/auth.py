from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class StaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["staff"] = "staff"

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3 or not all(char.isascii() and (char.isalnum() or char in "_.-") for char in value):
            raise ValueError("Username must be 3–50 characters and use letters, numbers, dot, underscore, or hyphen.")
        return value


class StaffUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr | None = None
    role: Literal["admin", "staff"] | None = None

    @field_validator("username")
    @classmethod
    def clean_optional_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 3 or not all(char.isascii() and (char.isalnum() or char in "_.-") for char in value):
            raise ValueError("Username must be 3–50 characters and use letters, numbers, dot, underscore, or hyphen.")
        return value

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one staff profile field must be supplied.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Staff profile fields cannot be null.")
        return self


class StaffResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Literal["admin", "staff"]
    is_active: bool
    created_at: datetime
    is_last_active_admin: bool = False


class StaffDirectoryResponse(BaseModel):
    items: list[StaffResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    active_admin_count: int


class StaffLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: EmailStr
    role: str
