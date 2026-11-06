import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.products import router as products_router
from app.db.database import Base, get_db
from app.models.conversation import GuestSessionDB
from app.models.order import OrderItemDB
from app.models.product import ProductDB
from app.models.staff import StaffUserDB
from app.services.order_service import OrderStockError, create_order, update_order_status
from app.services.product_tool import search_products


class ProductManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = self.Session()
        self.api = FastAPI()
        self.api.include_router(products_router)

        def override_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        self.api.dependency_overrides[get_db] = override_db
        self.client = TestClient(self.api)

    def tearDown(self):
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def set_role(self, role):
        self.api.dependency_overrides[get_current_user] = lambda: StaffUserDB(
            id=4,
            username="catalogue-manager",
            email="manager@example.test",
            password_hash="unused",
            role=role,
            is_active=True,
        )

    @staticmethod
    def product_payload(**changes):
        payload = {
            "name": "Basmati Rice",
            "category": "Grocery",
            "price": "180.00",
            "unit": "kg",
            "stock": 10,
            "description": "Premium long-grain basmati rice.",
            "brand": "Lasata Select",
        }
        payload.update(changes)
        return payload

    def test_staff_reads_admin_manages_and_catalogue_filters(self):
        self.assertEqual(self.client.get("/api/v1/products/staff/all").status_code, 401)
        self.set_role("staff")
        self.assertEqual(self.client.get("/api/v1/products/staff/all").status_code, 200)
        denied = self.client.post("/api/v1/products/staff", json=self.product_payload())
        self.assertEqual(denied.status_code, 403)

        self.set_role("admin")
        created = self.client.post("/api/v1/products/staff", json=self.product_payload())
        self.assertEqual(created.status_code, 201, created.text)
        product_id = created.json()["id"]
        out_of_stock = self.client.post(
            "/api/v1/products/staff",
            json=self.product_payload(name="Chocolate", category="Snacks", stock=0, brand="Lasata Snacks"),
        )
        self.assertEqual(out_of_stock.status_code, 201)

        duplicate = self.client.post("/api/v1/products/staff", json=self.product_payload())
        self.assertEqual(duplicate.status_code, 409)
        available = self.client.get("/api/v1/products/staff/all", params={"availability": "available", "category": "grocery", "page_size": 1})
        self.assertEqual(available.status_code, 200)
        self.assertEqual(available.json()["total"], 1)
        self.assertEqual(available.json()["items"][0]["id"], product_id)
        unavailable = self.client.get("/api/v1/products/staff/all", params={"availability": "out_of_stock"})
        self.assertEqual([item["name"] for item in unavailable.json()["items"]], ["Chocolate"])
        self.assertIn("Grocery", available.json()["categories"])

    def test_validation_stock_search_order_snapshots_and_safe_delete(self):
        self.set_role("admin")
        for invalid in (
            self.product_payload(name="   "),
            self.product_payload(price="-0.01"),
            self.product_payload(price="12.345"),
            self.product_payload(stock=-1),
        ):
            with self.subTest(payload=invalid):
                self.assertEqual(self.client.post("/api/v1/products/staff", json=invalid).status_code, 422)

        created = self.client.post("/api/v1/products/staff", json=self.product_payload())
        self.assertEqual(created.status_code, 201, created.text)
        product_id = created.json()["id"]
        invalid_stock = self.client.patch(f"/api/v1/products/staff/{product_id}/stock", json={"stock": -3})
        self.assertEqual(invalid_stock.status_code, 422)

        guest = GuestSessionDB(
            token_hash="product-order-session".ljust(64, "0"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(guest)
        self.db.commit()
        order = create_order(
            db=self.db,
            guest_session_id=guest.id,
            customer_name="Customer",
            customer_phone="9800000000",
            delivery_location="Damauli",
            ward_number=2,
            items=[{"product_id": product_id, "quantity": 2}],
        )
        self.assertEqual(self.db.get(ProductDB, product_id).stock, 10)
        item = self.db.query(OrderItemDB).filter(OrderItemDB.order_id == order.id).one()
        self.assertEqual(item.product_name, "Basmati Rice")
        self.assertEqual(item.unit_price, Decimal("180.00"))

        self.assertEqual(self.client.patch(f"/api/v1/products/staff/{product_id}/stock", json={"stock": 1}).status_code, 200)
        with self.assertRaises(OrderStockError):
            update_order_status(self.db, order.id, "confirmed")
        self.assertEqual(self.db.get(ProductDB, product_id).stock, 1)
        self.assertEqual(self.client.patch(f"/api/v1/products/staff/{product_id}/stock", json={"stock": 8}).status_code, 200)
        updated = self.client.patch(
            f"/api/v1/products/staff/{product_id}",
            json={"name": "Basmati Rice Premium", "price": "200.00", "description": "Updated description."},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        found = search_products(self.db, "Premium", limit=5)
        self.assertEqual(found[0]["name"], "Basmati Rice Premium")
        self.assertEqual(found[0]["price"], 200.0)
        self.assertEqual(found[0]["stock"], 8)
        self.assertEqual(item.product_name, "Basmati Rice")
        self.assertEqual(item.unit_price, Decimal("180.00"))

        confirmed = update_order_status(self.db, order.id, "confirmed")
        self.assertEqual(confirmed.status, "confirmed")
        self.assertEqual(self.db.get(ProductDB, product_id).stock, 6)
        cancelled = update_order_status(self.db, order.id, "cancelled")
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(self.db.get(ProductDB, product_id).stock, 8)

        protected_delete = self.client.delete(f"/api/v1/products/staff/{product_id}")
        self.assertEqual(protected_delete.status_code, 409)
        self.assertIsNotNone(self.db.get(ProductDB, product_id))
        stock_lookup = self.client.get(f"/api/v1/products/{product_id}/stock")
        self.assertEqual(stock_lookup.status_code, 200)
        self.assertEqual(stock_lookup.json()["stock"], 8)

        disposable = self.client.post("/api/v1/products/staff", json=self.product_payload(name="One-off item"))
        self.assertEqual(disposable.status_code, 201)
        deleted = self.client.delete(f"/api/v1/products/staff/{disposable.json()['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/products/{disposable.json()['id']}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
