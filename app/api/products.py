from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.schemas.product import Product, ProductListResponse
from app.schemas.product_management import (
    ProductAvailability,
    ProductCreate,
    ProductManagementDetail,
    ProductManagementPage,
    ProductStockUpdate,
    ProductUpdate,
)
from app.services.product_management_service import (
    DuplicateProductError,
    ProductInUseError,
    create_product,
    delete_product,
    get_product,
    list_products as list_managed_products,
    update_product,
    update_product_stock,
)
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


@router.get("/staff/all", response_model=ProductManagementPage)
def list_staff_products(
    search: str | None = Query(default=None, max_length=150),
    category: str | None = Query(default=None, max_length=100),
    availability: ProductAvailability | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return list_managed_products(
        db,
        search=search,
        category=category,
        availability=availability,
        page=page,
        page_size=page_size,
    )


@router.get("/staff/{product_id}", response_model=ProductManagementDetail)
def retrieve_staff_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.post("/staff", response_model=ProductManagementDetail, status_code=status.HTTP_201_CREATED)
def add_staff_product(
    request: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    try:
        return create_product(db, request.model_dump())
    except DuplicateProductError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/staff/{product_id}", response_model=ProductManagementDetail)
def edit_staff_product(
    product_id: int,
    request: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    try:
        product = update_product(db, product_id, request.model_dump(exclude_unset=True))
    except DuplicateProductError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.patch("/staff/{product_id}/stock", response_model=ProductManagementDetail)
def change_staff_product_stock(
    product_id: int,
    request: ProductStockUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    product = update_product_stock(db, product_id, request.stock)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.delete("/staff/{product_id}")
def remove_staff_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    try:
        deleted = delete_product(db, product_id)
    except ProductInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"success": True, "product_id": product_id, "message": "Product deleted."}


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
