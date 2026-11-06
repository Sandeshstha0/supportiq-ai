from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.order import OrderItemDB
from app.models.product import ProductDB


class DuplicateProductError(ValueError):
    pass


class ProductInUseError(ValueError):
    pass


def _duplicate_exists(db: Session, values: dict, exclude_id: int | None = None) -> bool:
    query = db.query(ProductDB.id).filter(
        func.lower(ProductDB.name) == values["name"].strip().lower(),
        func.lower(ProductDB.brand) == values["brand"].strip().lower(),
        func.lower(ProductDB.category) == values["category"].strip().lower(),
        func.lower(ProductDB.unit) == values["unit"].strip().lower(),
    )
    if exclude_id is not None:
        query = query.filter(ProductDB.id != exclude_id)
    return query.first() is not None


def _product_data(product: ProductDB, has_order_history: bool = False) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "unit": product.unit,
        "stock": product.stock,
        "description": product.description,
        "brand": product.brand,
        "has_order_history": has_order_history,
    }


def list_products(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    availability: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(ProductDB)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(
            ProductDB.name.ilike(pattern),
            ProductDB.brand.ilike(pattern),
            ProductDB.category.ilike(pattern),
        ))
    if category and category.strip():
        query = query.filter(func.lower(ProductDB.category) == category.strip().lower())
    if availability == "available":
        query = query.filter(ProductDB.stock > 0)
    elif availability == "out_of_stock":
        query = query.filter(ProductDB.stock == 0)

    total = query.count()
    products = (
        query.order_by(ProductDB.name.asc(), ProductDB.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ids = [product.id for product in products]
    history_counts = {
        product_id: count
        for product_id, count in db.query(
            OrderItemDB.product_id,
            func.count(OrderItemDB.id),
        ).filter(OrderItemDB.product_id.in_(ids)).group_by(OrderItemDB.product_id).all()
    } if ids else {}
    categories = [category for (category,) in db.query(ProductDB.category).distinct().order_by(ProductDB.category).all()]
    return {
        "items": [_product_data(product, history_counts.get(product.id, 0) > 0) for product in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "categories": categories,
    }


def get_product(db: Session, product_id: int) -> dict | None:
    product = db.get(ProductDB, product_id)
    if product is None:
        return None
    has_order_history = db.query(OrderItemDB.id).filter(
        OrderItemDB.product_id == product_id,
    ).first() is not None
    return _product_data(product, has_order_history)


def create_product(db: Session, values: dict) -> dict:
    values = dict(values)
    values["price"] = Decimal(values["price"])
    if _duplicate_exists(db, values):
        raise DuplicateProductError("A product with the same name, brand, category, and unit already exists.")
    product = ProductDB(**values)
    db.add(product)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateProductError("The product conflicts with an existing catalogue record.") from exc
    return _product_data(product)


def update_product(db: Session, product_id: int, values: dict) -> dict | None:
    product = db.get(ProductDB, product_id)
    if product is None:
        return None
    changes = dict(values)
    merged = {
        "name": changes.get("name", product.name),
        "brand": changes.get("brand", product.brand),
        "category": changes.get("category", product.category),
        "unit": changes.get("unit", product.unit),
    }
    if _duplicate_exists(db, merged, exclude_id=product_id):
        raise DuplicateProductError("Another product has the same name, brand, category, and unit.")
    if "price" in changes:
        changes["price"] = Decimal(changes["price"])
    for key, value in changes.items():
        setattr(product, key, value)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateProductError("The product conflicts with an existing catalogue record.") from exc
    return get_product(db, product_id)


def update_product_stock(db: Session, product_id: int, stock: int) -> dict | None:
    product = db.get(ProductDB, product_id)
    if product is None:
        return None
    product.stock = stock
    db.commit()
    db.refresh(product)
    return get_product(db, product_id)


def delete_product(db: Session, product_id: int) -> bool:
    product = db.get(ProductDB, product_id)
    if product is None:
        return False
    if db.query(OrderItemDB.id).filter(OrderItemDB.product_id == product_id).first():
        raise ProductInUseError("This product appears in order history and cannot be deleted. Set stock to zero to make it unavailable.")
    db.delete(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ProductInUseError("This product is referenced by an order and cannot be deleted.") from exc
    return True
