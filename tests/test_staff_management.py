import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.api.dependencies import get_current_user
from app.db.database import Base, get_db
from app.models.staff import StaffUserDB
from app.services.auth_service import verify_password
from app.services.staff_management_service import (
    LastActiveAdminError,
    StaffProtectionError,
    update_staff_member,
    update_staff_status,
)


class StaffManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = self.Session()
        self.admin = StaffUserDB(
            username="admin.root",
            email="admin@example.com",
            password_hash="unused-hash",
            role="admin",
            is_active=True,
        )
        self.db.add(self.admin)
        self.db.commit()
        self.api = FastAPI()
        self.api.include_router(auth_router)

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

    def set_principal(self, user):
        self.api.dependency_overrides[get_current_user] = lambda: user

    def staff_payload(self, **changes):
        payload = {
            "username": "support.agent",
            "email": "agent@example.com",
            "password": "a-secure-password-123",
            "role": "staff",
        }
        payload.update(changes)
        return payload

    def test_only_admin_can_list_view_create_edit_and_update_status(self):
        self.assertEqual(self.client.get("/api/v1/auth/staff").status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/auth/staff/{self.admin.id}").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/auth/staff", json=self.staff_payload()).status_code, 401)

        staff_principal = StaffUserDB(
            id=22,
            username="regular.staff",
            email="regular@example.com",
            password_hash="unused",
            role="staff",
            is_active=True,
        )
        self.set_principal(staff_principal)
        self.assertEqual(self.client.get("/api/v1/auth/staff?page=1&page_size=20").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/staff", json=self.staff_payload()).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/auth/staff/{self.admin.id}/status?is_active=false").status_code, 403)

        self.set_principal(self.admin)
        # The no-query list remains compatible with the original array response.
        self.assertIsInstance(self.client.get("/api/v1/auth/staff").json(), list)
        created = self.client.post("/api/v1/auth/staff", json=self.staff_payload())
        self.assertEqual(created.status_code, 201, created.text)
        account = created.json()["staff"]
        staff_id = account["id"]
        self.assertNotIn("password_hash", account)
        saved = self.db.get(StaffUserDB, staff_id)
        self.assertNotEqual(saved.password_hash, "a-secure-password-123")
        self.assertTrue(verify_password("a-secure-password-123", saved.password_hash))

        page = self.client.get("/api/v1/auth/staff", params={"search": "SUPPORT", "page": 1, "page_size": 1})
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json()["total"], 1)
        self.assertEqual(page.json()["items"][0]["id"], staff_id)
        self.assertNotIn("password_hash", page.json()["items"][0])
        detail = self.client.get(f"/api/v1/auth/staff/{staff_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("password_hash", detail.json())

        duplicate = self.client.post("/api/v1/auth/staff", json=self.staff_payload(username="SUPPORT.AGENT"))
        self.assertEqual(duplicate.status_code, 409)
        invalid = self.client.post("/api/v1/auth/staff", json=self.staff_payload(username="x"))
        self.assertEqual(invalid.status_code, 422)

        updated = self.client.patch(
            f"/api/v1/auth/staff/{staff_id}",
            json={"username": "agent.updated", "email": "updated@example.com", "role": "admin"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["staff"]["role"], "admin")
        self.assertEqual(updated.json()["staff"]["username"], "agent.updated")
        invalid_role = self.client.patch(f"/api/v1/auth/staff/{staff_id}", json={"role": "manager"})
        self.assertEqual(invalid_role.status_code, 422)

        deactivated = self.client.patch(f"/api/v1/auth/staff/{staff_id}/status?is_active=false")
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()["staff"]["is_active"])
        activated = self.client.patch(f"/api/v1/auth/staff/{staff_id}/status?is_active=true")
        self.assertEqual(activated.status_code, 200)
        self.assertTrue(activated.json()["staff"]["is_active"])

    def test_self_and_last_active_admin_protections(self):
        self.set_principal(self.admin)
        self_deactivate = self.client.patch(f"/api/v1/auth/staff/{self.admin.id}/status?is_active=false")
        self.assertEqual(self_deactivate.status_code, 400)
        self_demote = self.client.patch(f"/api/v1/auth/staff/{self.admin.id}", json={"role": "staff"})
        self.assertEqual(self_demote.status_code, 400)
        self.assertTrue(self.db.get(StaffUserDB, self.admin.id).is_active)

        # Exercise the last-admin guard for an administrator acting on another account.
        with self.assertRaises(LastActiveAdminError):
            update_staff_status(self.db, self.admin.id, False, current_admin_id=self.admin.id + 100)
        with self.assertRaises(LastActiveAdminError):
            update_staff_member(self.db, self.admin.id, {"role": "staff"}, current_admin_id=self.admin.id + 100)
        self.assertEqual(
            self.db.query(StaffUserDB).filter(StaffUserDB.role == "admin", StaffUserDB.is_active.is_(True)).count(),
            1,
        )

    def test_profile_edit_conflicts_and_inactive_staff_cannot_login(self):
        self.set_principal(self.admin)
        created = self.client.post("/api/v1/auth/staff", json=self.staff_payload())
        staff_id = created.json()["staff"]["id"]
        conflict = self.client.patch(f"/api/v1/auth/staff/{staff_id}", json={"email": self.admin.email})
        self.assertEqual(conflict.status_code, 409)

        deactivated = self.client.patch(f"/api/v1/auth/staff/{staff_id}/status?is_active=false")
        self.assertEqual(deactivated.status_code, 200)
        login = self.client.post("/api/v1/auth/login", json={"username": "support.agent", "password": "a-secure-password-123"})
        self.assertEqual(login.status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/auth/staff/{999999}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
