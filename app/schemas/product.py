from decimal import Decimal

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: Decimal = Field(ge=0)
    unit: str
    stock: int = Field(ge=0)
    description: str
    brand: str


class ProductListResponse(BaseModel):
    total: int
    products: list[Product]