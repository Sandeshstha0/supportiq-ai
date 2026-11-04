
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.product import ProductDB
from app.models.order import OrderDB, OrderItemDB


def create_order(
    db: Session,
    guest_session_id: int,
    customer_name: str,
    customer_phone: str,
    delivery_location: str,
    ward_number: int,
    items: list[dict],
    customer_email: str | None = None,
) -> OrderDB:
    """
    Create a customer order request.

    Prices and totals are calculated using database product prices.
    New orders remain pending_confirmation until staff reviews them.
    """

    if not items:
        raise ValueError("Order must contain at least one product.")

    try:
        order_items = []
        total_amount = Decimal("0.00")

        for item in items:
            product_id = item.get("product_id")
            quantity = Decimal(str(item.get("quantity", 0)))

            if quantity <= 0:
                raise ValueError("Product quantity must be greater than zero.")

            product = (
                db.query(ProductDB)
                .filter(ProductDB.id == product_id)
                .with_for_update()
                .first()
            )

            if not product:
                raise ValueError(f"Product with ID {product_id} was not found.")

            if Decimal(str(product.stock)) < quantity:
                raise ValueError(
                    f"Insufficient stock for {product.name}. "
                    f"Available stock: {product.stock}"
                )

            unit_price = Decimal(str(product.price))
            subtotal = unit_price * quantity
            total_amount += subtotal

            order_items.append(
                OrderItemDB(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        order = OrderDB(
            guest_session_id=guest_session_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            delivery_location=delivery_location,
            ward_number=ward_number,
            total_amount=total_amount,
            status="pending_confirmation",
        )

        order.items = order_items

        db.add(order)
        db.commit()
        db.refresh(order)

        return order

    except (InvalidOperation, TypeError) as exc:
        db.rollback()
        raise ValueError("Invalid product quantity.") from exc

    except Exception:
        db.rollback()
        raise
