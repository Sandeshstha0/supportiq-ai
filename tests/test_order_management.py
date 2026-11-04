import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.orders import router as orders_router
from app.api.customers import router as customers_router
from app.api.tickets import router as tickets_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.db.database import Base, get_db
from app.models.conversation import ConversationDB, GuestSessionDB, MessageDB
from app.models.order import OrderDB, OrderItemDB
from app.models.product import ProductDB
from app.models.staff import StaffUserDB
from app.models.ticket import SupportTicketDB
from app.services.order_service import (
    OrderStatusTransitionError,
    update_order_status,
)
from app.services.guest_session_service import create_guest_session


class OrderManagementTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        self.engine = engine
        self.db = self.Session()
        self.guest_session = GuestSessionDB(
            token_hash="test-session-token-hash".ljust(64, "0"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(self.guest_session)
        self.db.commit()
        self.db.add(ProductDB(
            id=1,
            name="Rice",
            category="Grocery",
            price=Decimal("100.00"),
            unit="kg",
            stock=10,
            description="Long grain rice",
            brand="Lasata",
        ))
        self.order = OrderDB(
            guest_session_id=self.guest_session.id,
            customer_name="Test Customer",
            customer_phone="9800000000",
            customer_email=None,
            delivery_location="Damauli",
            ward_number=2,
            total_amount=Decimal("200.00"),
            status="pending_confirmation",
            items=[OrderItemDB(
                product_id=1,
                product_name="Rice",
                quantity=Decimal("2"),
                unit_price=Decimal("100.00"),
                subtotal=Decimal("200.00"),
            )],
        )
        self.db.add(self.order)
        self.db.commit()
        self.order_id = self.order.id

        self.api = FastAPI()
        self.api.include_router(orders_router)
        self.api.include_router(customers_router)
        self.api.include_router(tickets_router)
        self.api.include_router(chat_router)
        self.api.include_router(conversations_router)

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

    def authorize_staff(self):
        self.api.dependency_overrides[get_current_user] = lambda: StaffUserDB(
            id=7,
            username="agent",
            email="agent@example.test",
            password_hash="unused",
            role="staff",
            is_active=True,
        )

    def test_staff_order_routes_reject_unauthenticated_requests(self):
        response = self.client.get("/api/v1/orders/staff/all")
        self.assertEqual(response.status_code, 401)

    def test_staff_conversation_routes_require_authentication_and_filter(self):
        first = ConversationDB(guest_session_id=self.guest_session.id)
        second = ConversationDB(guest_session_id=None)
        self.db.add_all([first, second])
        self.db.flush()
        self.db.add_all([
            MessageDB(conversation_id=first.id, role="user", content="Help with an order", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            MessageDB(conversation_id=first.id, role="assistant", content="I can help", created_at=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)),
        ])
        self.db.commit()
        self.assertEqual(self.client.get("/api/v1/conversations/staff/all").status_code, 401)

        self.authorize_staff()
        response = self.client.get("/api/v1/conversations/staff/all", params={"search": str(self.guest_session.id), "page_size": 1})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["id"], first.id)
        self.assertEqual(payload["items"][0]["message_count"], 2)
        self.assertTrue(payload["items"][0]["has_customer_profile"])

        details = self.client.get(f"/api/v1/conversations/staff/{first.id}")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/conversations/staff/999999").status_code, 404)
        messages = details.json()["messages"]
        self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
        self.assertLessEqual(messages[0]["created_at"], messages[1]["created_at"])
        invalid_dates = self.client.get("/api/v1/conversations/staff/all", params={"date_from": "2026-02-01", "date_to": "2026-01-01"})
        self.assertEqual(invalid_dates.status_code, 400)

    def test_guest_conversation_endpoints_keep_guest_session_ownership(self):
        token, _ = create_guest_session(self.db)
        session = self.db.query(GuestSessionDB).filter(GuestSessionDB.id != self.guest_session.id).one()
        conversation = ConversationDB(guest_session_id=session.id)
        self.db.add(conversation)
        self.db.flush()
        self.db.add(MessageDB(conversation_id=conversation.id, role="user", content="Guest message"))
        self.db.commit()

        listing = self.client.get("/api/v1/chat/conversations", headers={"X-Guest-Session": token})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["conversations"][0]["conversation_id"], conversation.id)
        history = self.client.get(f"/api/v1/chat/conversations/{conversation.id}", headers={"X-Guest-Session": token})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["messages"][0]["content"], "Guest message")

    def test_search_and_status_filter_are_paginated(self):
        self.authorize_staff()
        for term in (str(self.order_id), "Test Customer", "9800000000"):
            with self.subTest(search=term):
                response = self.client.get(
                    "/api/v1/orders/staff/all",
                    params={"search": term, "status": "pending_confirmation", "page": 1, "page_size": 1},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["total"], 1)
                self.assertEqual(payload["page_size"], 1)
                self.assertEqual(payload["items"][0]["customer_name"], "Test Customer")

    def test_staff_detail_and_status_endpoints_return_complete_order(self):
        self.authorize_staff()

        detail = self.client.get(f"/api/v1/orders/staff/{self.order_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["items"][0]["product_name"], "Rice")

        updated = self.client.patch(
            f"/api/v1/orders/staff/{self.order_id}/status",
            json={"status": "confirmed"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "confirmed")

        invalid = self.client.patch(
            f"/api/v1/orders/staff/{self.order_id}/status",
            json={"status": "delivered"},
        )
        self.assertEqual(invalid.status_code, 409)
        self.assertEqual(self.db.get(ProductDB, 1).stock, 8)

    def test_guest_order_creation_remains_pending_without_reserving_stock(self):
        session_token, _ = create_guest_session(self.db)
        response = self.client.post(
            "/api/v1/orders",
            headers={"X-Guest-Session": session_token},
            json={
                "customer_name": "New Customer",
                "customer_phone": "9800000001",
                "delivery_location": "Damauli",
                "ward_number": 3,
                "items": [{"product_id": 1, "quantity": 2}],
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "pending_confirmation")
        self.assertEqual(self.db.get(ProductDB, 1).stock, 10)

    def test_customer_directory_searches_and_pages_guest_sessions(self):
        self.authorize_staff()
        second_session = GuestSessionDB(
            token_hash="second-session-token-hash".ljust(64, "1"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(second_session)
        self.db.flush()
        self.db.add(OrderDB(
            guest_session_id=second_session.id,
            customer_name="Test Customer",
            customer_phone="9800000000",
            customer_email=None,
            delivery_location="Damauli",
            ward_number=2,
            total_amount=Decimal("50.00"),
            status="pending_confirmation",
        ))
        self.db.commit()

        response = self.client.get("/api/v1/customers/staff/all", params={"search": "Test Customer", "page": 1, "page_size": 1})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["page_size"], 1)
        self.assertEqual(payload["summary"]["total_guest_sessions"], 2)
        self.assertEqual(payload["items"][0]["identity_type"], "guest_session")
        self.assertIn("not verified person", payload["identity_note"])

    def test_customer_detail_only_includes_records_for_exact_guest_session(self):
        self.authorize_staff()
        ticket = SupportTicketDB(
            guest_session_id=self.guest_session.id,
            customer_name="Test Customer",
            customer_email=None,
            customer_phone="9800000000",
            category="delivery",
            subject="Delivery question",
            description="Where is my order?",
            status="open",
        )
        conversation = ConversationDB(guest_session_id=self.guest_session.id)
        self.db.add_all([ticket, conversation])
        self.db.flush()
        self.db.add(MessageDB(
            conversation_id=conversation.id,
            role="user",
            content="Can you help with my delivery?",
        ))
        self.db.commit()

        response = self.client.get(f"/api/v1/customers/staff/{self.guest_session.id}")
        self.assertEqual(response.status_code, 200)
        details = response.json()
        self.assertEqual(details["order_count"], 1)
        self.assertEqual(details["ticket_count"], 1)
        self.assertEqual(details["conversation_count"], 1)
        self.assertEqual(details["conversations"][0]["messages"][0]["content"], "Can you help with my delivery?")
        self.assertEqual({item["type"] for item in details["activity"]}, {"order_created", "ticket_created", "conversation_started"})

    def test_customer_endpoints_reject_unauthenticated_requests(self):
        response = self.client.get("/api/v1/customers/staff/all")
        self.assertEqual(response.status_code, 401)

    def _create_ticket(self, subject="Delivery question", status="open", category="delivery"):
        ticket = SupportTicketDB(
            guest_session_id=self.guest_session.id,
            customer_name="Test Customer",
            customer_email="customer@example.test",
            customer_phone="9800000000",
            category=category,
            subject=subject,
            description="Please help with a recent delivery.",
            status=status,
        )
        self.db.add(ticket)
        self.db.commit()
        return ticket

    def test_staff_ticket_listing_search_filters_and_pagination(self):
        self.authorize_staff()
        first = self._create_ticket("Delivery question")
        self._create_ticket("Payment question", category="billing")

        for search_term in (str(first.id), "Test Customer", "9800000000", "customer@example.test"):
            with self.subTest(search=search_term):
                response = self.client.get(
                    "/api/v1/tickets/staff/all",
                    params={"search": search_term, "status_filter": "open", "category": "delivery", "page": 1, "page_size": 1},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["total"], 1)
                self.assertEqual(payload["items"][0]["id"], first.id)

    def test_ticket_detail_update_and_duplicate_update_email_behavior(self):
        self.authorize_staff()
        ticket = self._create_ticket()
        detail = self.client.get(f"/api/v1/tickets/staff/{ticket.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["guest_session_id"], self.guest_session.id)
        self.assertIsNone(detail.json()["decision"])

        body = {"decision": "We are checking the delivery status.", "status": "in_progress"}
        with patch("app.api.tickets.send_ticket_decision_email", return_value=True) as send_email:
            first_update = self.client.patch(f"/api/v1/tickets/{ticket.id}/decision", json=body)
            duplicate_update = self.client.patch(f"/api/v1/tickets/{ticket.id}/decision", json=body)
            self.assertEqual(first_update.status_code, 200)
            self.assertEqual(duplicate_update.status_code, 200)
            self.assertTrue(first_update.json()["email_notification_sent"])
            self.assertFalse(duplicate_update.json()["email_notification_sent"])
            self.assertEqual(send_email.call_count, 1)

    def test_ticket_transition_rules_reject_invalid_moves_and_status_values(self):
        self.authorize_staff()
        ticket = self._create_ticket(status="resolved")
        invalid_transition = self.client.patch(
            f"/api/v1/tickets/{ticket.id}/decision",
            json={"decision": "Requesting an unsupported reopen.", "status": "open"},
        )
        self.assertEqual(invalid_transition.status_code, 409)
        invalid_status = self.client.patch(
            f"/api/v1/tickets/{ticket.id}/decision",
            json={"decision": "A rejected state is not defined.", "status": "rejected"},
        )
        self.assertEqual(invalid_status.status_code, 422)

    def test_guest_ticket_creation_and_confirmation_email_remain_unchanged(self):
        session_token, _ = create_guest_session(self.db)
        body = {
            "category": "delivery",
            "subject": "Order arrival question",
            "description": "Please let me know the status of my delivery.",
            "customer_name": "Guest Customer",
            "customer_email": "guest@example.test",
        }
        with patch("app.api.tickets.send_ticket_confirmation_email", return_value=True) as send_email:
            response = self.client.post(
                "/api/v1/tickets",
                headers={"X-Guest-Session": session_token},
                json=body,
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["status"], "open")
            send_email.assert_called_once()

    def test_staff_ticket_endpoint_requires_authentication(self):
        response = self.client.get("/api/v1/tickets/staff/all")
        self.assertEqual(response.status_code, 401)

    def test_confirmation_reserves_stock_once_and_cancellation_releases_it(self):
        confirmed = update_order_status(self.db, self.order_id, "confirmed")
        self.assertEqual(confirmed.status, "confirmed")
        self.assertEqual(self.db.get(ProductDB, 1).stock, 8)

        with self.assertRaises(OrderStatusTransitionError):
            update_order_status(self.db, self.order_id, "confirmed")
        self.assertEqual(self.db.get(ProductDB, 1).stock, 8)

        cancelled = update_order_status(self.db, self.order_id, "cancelled")
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(self.db.get(ProductDB, 1).stock, 10)

    def test_invalid_transition_does_not_change_order_or_stock(self):
        with self.assertRaises(OrderStatusTransitionError):
            update_order_status(self.db, self.order_id, "delivered")
        self.assertEqual(self.db.get(OrderDB, self.order_id).status, "pending_confirmation")
        self.assertEqual(self.db.get(ProductDB, 1).stock, 10)


if __name__ == "__main__":
    unittest.main()
