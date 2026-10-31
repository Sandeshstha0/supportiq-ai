from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.product import Product, ProductListResponse
from app.services.product_service import (
    get_products,
    get_product_by_id,
)

router = APIRouter(
    prefix="/api/v1/products",
    tags=["Products"],
)


@router.get("", response_model=ProductListResponse)
def list_products(
    search: str | None = Query(default=None, min_length=1),
    category: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    products = get_products(
        db=db,
        search=search,
        category=category,
    )

    return {
        "total": len(products),
        "products": products,
    }


@router.get("/{product_id}", response_model=Product)
def retrieve_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = get_product_by_id(db, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.get("/{product_id}/stock")
def check_product_stock(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = get_product_by_id(db, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return {
        "product_id": product.id,
        "product_name": product.name,
        "stock": product.stock,
        "available": product.stock > 0,
        "unit": product.unit,
    }