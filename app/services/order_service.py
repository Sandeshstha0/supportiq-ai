
from decimal import Decimal, InvalidOperation

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.product import ProductDB
from app.models.order import OrderDB, OrderItemDB


VALID_ORDER_STATUSES = {
    "pending_confirmation",
    "confirmed",
    "processing",
    "out_for_delivery",
    "delivered",
    "cancelled",
}

ORDER_STATUS_TRANSITIONS = {
    "pending_confirmation": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"out_for_delivery", "cancelled"},
    "out_for_delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


class OrderNotFoundError(Exception):
    pass


class OrderStatusTransitionError(ValueError):
    pass


class OrderStockError(ValueError):
    pass


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


def get_staff_orders(
    db: Session,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(OrderDB)

    if status:
        query = query.filter(OrderDB.status == status)

    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            query = query.filter(or_(
                cast(OrderDB.id, String).ilike(pattern),
                OrderDB.customer_name.ilike(pattern),
                OrderDB.customer_phone.ilike(pattern),
            ))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    orders = (
        query.options(selectinload(OrderDB.items))
        .order_by(OrderDB.created_at.desc(), OrderDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_staff_order(db: Session, order_id: int) -> OrderDB | None:
    return (
        db.query(OrderDB)
        .options(selectinload(OrderDB.items))
        .filter(OrderDB.id == order_id)
        .first()
    )


def _order_quantities_by_product(order: OrderDB) -> dict[int, Decimal]:
    quantities: dict[int, Decimal] = {}
    for item in order.items:
        quantities[item.product_id] = quantities.get(item.product_id, Decimal("0")) + Decimal(str(item.quantity))
    return quantities


def _locked_products(db: Session, product_ids: list[int]) -> dict[int, ProductDB]:
    products: dict[int, ProductDB] = {}
    for product_id in sorted(product_ids):
        product = (
            db.query(ProductDB)
            .filter(ProductDB.id == product_id)
            .with_for_update()
            .first()
        )
        if product is None:
            raise OrderStockError(f"Product {product_id} is no longer available.")
        products[product_id] = product
    return products


def update_order_status(
    db: Session,
    order_id: int,
    new_status: str,
) -> OrderDB:
    if new_status not in VALID_ORDER_STATUSES:
        raise OrderStatusTransitionError("Invalid order status.")

    try:
        order = (
            db.query(OrderDB)
            .options(selectinload(OrderDB.items))
            .filter(OrderDB.id == order_id)
            .with_for_update()
            .first()
        )
        if order is None:
            raise OrderNotFoundError

        current_status = order.status
        if new_status not in ORDER_STATUS_TRANSITIONS.get(current_status, set()):
            raise OrderStatusTransitionError(
                f"Order cannot transition from {current_status} to {new_status}."
            )

        quantities = _order_quantities_by_product(order)

        if new_status == "confirmed":
            products = _locked_products(db, list(quantities))
            for product_id, quantity in quantities.items():
                product = products[product_id]
                if quantity != quantity.to_integral_value():
                    raise OrderStockError(
                        f"{product.name} has fractional order quantity, but inventory is tracked in whole units."
                    )
                if Decimal(product.stock) < quantity:
                    raise OrderStockError(
                        f"Insufficient stock for {product.name}. Available stock: {product.stock}."
                    )
            for product_id, quantity in quantities.items():
                products[product_id].stock -= int(quantity)

        elif new_status == "cancelled" and current_status in {"confirmed", "processing"}:
            products = _locked_products(db, list(quantities))
            for product_id, quantity in quantities.items():
                if quantity != quantity.to_integral_value():
                    raise OrderStockError(
                        "Cannot release fractional quantities because inventory is tracked in whole units."
                    )
            for product_id, quantity in quantities.items():
                products[product_id].stock += int(quantity)

        order.status = new_status
        db.commit()
        return get_staff_order(db, order_id)

    except Exception:
        db.rollback()
        raise
