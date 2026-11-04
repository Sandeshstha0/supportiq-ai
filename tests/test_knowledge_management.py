import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.api.dependencies import get_current_user
from app.api.knowledge import router as knowledge_router
from app.models.staff import StaffUserDB
from app.services.knowledge_search_service import search_knowledge
from app.services.qdrant_service import COLLECTION_NAME


class KnowledgeManagementTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.qdrant = QdrantClient(path=str(Path(self.tempdir.name) / "qdrant"))
        self.api = FastAPI()
        self.api.include_router(knowledge_router, prefix="/api/v1")
        self.client = TestClient(self.api)
        self._patch("app.services.knowledge_service.get_qdrant_client", return_value=self.qdrant)
        self._patch("app.services.knowledge_management_service.get_qdrant_client", return_value=self.qdrant)
        self._patch("app.services.knowledge_search_service.get_qdrant_client", return_value=self.qdrant)
        self._patch("app.services.knowledge_service.create_knowledge_collection", side_effect=self.ensure_collection)
        self._patch("app.services.knowledge_service.generate_embedding", side_effect=self.embedding)
        self._patch("app.services.knowledge_search_service.generate_embedding", side_effect=self.embedding)

    def _patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def ensure_collection(self):
        if COLLECTION_NAME not in {item.name for item in self.qdrant.get_collections().collections}:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    @staticmethod
    def embedding(_text):
        return [0.01] * 768

    def tearDown(self):
        self.client.close()
        self.qdrant.close()
        self.tempdir.cleanup()

    def set_role(self, role):
        self.api.dependency_overrides[get_current_user] = lambda: StaffUserDB(
            id=1,
            username="reviewer",
            email="reviewer@example.test",
            password_hash="unused",
            role=role,
            is_active=True,
        )

    def test_staff_reads_admin_manages_and_rag_survives_replace_and_delete(self):
        self.assertEqual(self.client.get("/api/v1/knowledge/staff/documents").status_code, 401)
        self.set_role("staff")
        self.assertEqual(self.client.get("/api/v1/knowledge/staff/documents").status_code, 200)
        denied = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("store.txt", b"Store policy text content", "text/plain")},
        )
        self.assertEqual(denied.status_code, 403)

        self.set_role("admin")
        uploaded = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("returns.txt", "Verified return policy details.", "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        original = uploaded.json()
        document_id = original["document_id"]

        duplicate = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("duplicate.txt", "Verified return policy details.", "text/plain")},
        )
        self.assertEqual(duplicate.status_code, 409)

        listing = self.client.get("/api/v1/knowledge/staff/documents", params={"search": "return"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["items"][0]["id"], document_id)
        details = self.client.get(f"/api/v1/knowledge/staff/documents/{document_id}")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()["chunks"][0]["text"], "Verified return policy details.")

        replaced = self.client.put(
            f"/api/v1/knowledge/staff/documents/{document_id}",
            files={"file": ("returns-updated.txt", "Updated and verified returns guidance.", "text/plain")},
        )
        self.assertEqual(replaced.status_code, 200, replaced.text)
        refreshed_details = self.client.get(f"/api/v1/knowledge/staff/documents/{document_id}")
        self.assertIn("Updated and verified", refreshed_details.json()["chunks"][0]["text"])
        results = search_knowledge("return guidance")
        self.assertTrue(any("Updated and verified" in item["text"] for item in results), repr(results))
        points, _ = self.qdrant.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
            with_payload=True,
            with_vectors=False,
        )
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].payload["document_id"], document_id)

        deleted = self.client.delete(f"/api/v1/knowledge/staff/documents/{document_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(search_knowledge("return guidance"), [])

    def test_only_utf8_txt_under_limits_is_accepted(self):
        self.set_role("admin")
        unsupported = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("rules.pdf", b"not a pdf parser", "application/pdf")},
        )
        self.assertEqual(unsupported.status_code, 415)
        too_large = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("rules.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
        )
        self.assertEqual(too_large.status_code, 413)
        invalid_encoding = self.client.post(
            "/api/v1/knowledge/staff/documents/upload",
            files={"file": ("rules.txt", b"\xff\xfe", "text/plain")},
        )
        self.assertEqual(invalid_encoding.status_code, 422)

    def test_embedding_failure_is_reported_without_storing_vectors(self):
        self.set_role("admin")
        with patch("app.services.knowledge_service.generate_embedding", side_effect=RuntimeError("embedding unavailable")):
            response = self.client.post(
                "/api/v1/knowledge/staff/documents/upload",
                files={"file": ("unavailable.txt", "Verified store information text.", "text/plain")},
            )
        self.assertEqual(response.status_code, 502)
        listing = self.client.get("/api/v1/knowledge/staff/documents")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["total"], 0)

    def test_legacy_qdrant_vectors_are_visible_but_not_deletable(self):
        self.ensure_collection()
        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(
                id=str(uuid4()),
                vector=self.embedding("old"),
                payload={"title": "Old policy", "source": "manual", "chunk_index": 0, "text": "Legacy stored text passage."},
            )],
            wait=True,
        )
        self.set_role("admin")
        retrieved = search_knowledge("old policy")
        self.assertTrue(any("Legacy stored text" in item["text"] for item in retrieved))
        rows = self.client.get("/api/v1/knowledge/staff/documents").json()["items"]
        legacy = next(row for row in rows if row["legacy"])
        response = self.client.delete(f"/api/v1/knowledge/staff/documents/{legacy['id']}")
        self.assertEqual(response.status_code, 409)
        points, _ = self.qdrant.scroll(collection_name=COLLECTION_NAME, limit=10, with_payload=True, with_vectors=False)
        self.assertEqual(len(points), 1)


if __name__ == "__main__":
    unittest.main()
