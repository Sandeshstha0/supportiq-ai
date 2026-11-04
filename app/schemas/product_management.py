from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductFields(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    unit: str = Field(min_length=1, max_length=30)
    description: str = Field(max_length=5000)
    brand: str = Field(min_length=1, max_length=100)

    @field_validator("name", "category", "unit", "brand")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return value.strip()


class ProductCreate(ProductFields):
    stock: int = Field(ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    description: str | None = Field(default=None, max_length=5000)
    brand: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name", "category", "unit", "description", "brand")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def require_a_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one product field must be supplied.")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Product fields cannot be null.")
        for name in ("name", "category", "unit", "brand"):
            if getattr(self, name) == "":
                raise ValueError(f"{name} cannot be blank.")
        return self


class ProductStockUpdate(BaseModel):
    stock: int = Field(ge=0)


class ProductManagementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    price: Decimal
    unit: str
    stock: int
    description: str
    brand: str
    has_order_history: bool = False


class ProductManagementPage(BaseModel):
    items: list[ProductManagementItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]


class ProductManagementDetail(ProductManagementItem):
    pass


ProductAvailability = Literal["available", "out_of_stock"]
