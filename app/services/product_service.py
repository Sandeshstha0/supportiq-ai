from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import ProductDB


def get_products(
    db: Session,
    search: str | None = None,
    category: str | None = None,
) -> list[ProductDB]:
    statement = select(ProductDB)

    if search:
        search_term = f"%{search.strip()}%"

        statement = statement.where(
            ProductDB.name.ilike(search_term)
            | ProductDB.description.ilike(search_term)
            | ProductDB.brand.ilike(search_term)
            | ProductDB.category.ilike(search_term)
        )

    if category:
        statement = statement.where(
            ProductDB.category.ilike(category.strip())
        )

    statement = statement.order_by(ProductDB.id)

    return list(db.scalars(statement).all())


def get_product_by_id(
    db: Session,
    product_id: int,
) -> ProductDB | None:
    return db.get(ProductDB, product_id)