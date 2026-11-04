
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=150)
    customer_phone: str = Field(min_length=7, max_length=30)
    customer_email: EmailStr | None = None
    delivery_location: str = Field(min_length=3, max_length=255)
    ward_number: int = Field(ge=1, le=35)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_phone: str
    customer_email: str | None
    delivery_location: str
    ward_number: int
    total_amount: Decimal
    status: str
    created_at: datetime
    items: list[OrderItemResponse]
