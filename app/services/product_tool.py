from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.product import ProductDB


def search_products(
    db: Session,
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    sort_by: str = "relevance",
    limit: int = 5,
) -> list[dict]:
    """Search and filter products in the store database."""

    query = query.strip()

    if not query:
        return []

    search_term = f"%{query}%"

    statement = select(ProductDB).where(
        or_(
            ProductDB.name.ilike(search_term),
            ProductDB.category.ilike(search_term),
            ProductDB.description.ilike(search_term),
            ProductDB.brand.ilike(search_term),
        )
    )

    # Filter by category when provided.
    if category:
        statement = statement.where(
            ProductDB.category.ilike(category.strip())
        )

    # Filter by maximum price when provided.
    if max_price is not None:
        statement = statement.where(
            ProductDB.price <= max_price
        )

    # Sort the matching products.
    if sort_by == "price_asc":
        statement = statement.order_by(ProductDB.price.asc())
    elif sort_by == "price_desc":
        statement = statement.order_by(ProductDB.price.desc())
    else:
        statement = statement.order_by(ProductDB.name.asc())

    # Restrict the number of returned products.
    statement = statement.limit(max(1, min(limit, 10)))

    products = db.scalars(statement).all()

    return [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "price": float(product.price),
            "unit": product.unit,
            "stock": product.stock,
            "brand": product.brand,
            "description": product.description,
        }
        for product in products
    ]