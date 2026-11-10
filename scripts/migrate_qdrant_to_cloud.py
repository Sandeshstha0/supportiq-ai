
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.services.qdrant_service import (
    get_qdrant_client,
    COLLECTION_NAME,
)
LOCAL_PATH = Path("./qdrant_storage").resolve()

# Keep True for the first run. This only previews the migration.
DRY_RUN = False


def main():
    local = QdrantClient(path=str(LOCAL_PATH))
    cloud = get_qdrant_client()

    try:
        local_points = []
        offset = None

        while True:
            records, offset = local.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            local_points.extend(records)

            if offset is None:
                break

        cloud_ids = set()
        offset = None

        while True:
            records, offset = cloud.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            cloud_ids.update(point.id for point in records)

            if offset is None:
                break

        missing = [
            point for point in local_points
            if point.id not in cloud_ids
        ]

        print(f"Local points: {len(local_points)}")
        print(f"Cloud points: {len(cloud_ids)}")
        print(f"New points to migrate: {len(missing)}")
        print(f"Existing IDs to skip: {len(local_points) - len(missing)}")

        if DRY_RUN:
            print("DRY RUN: No data was changed.")
            return

        batch = [
            PointStruct(
                id=point.id,
                vector=point.vector,
                payload=point.payload,
            )
            for point in missing
        ]

        if batch:
            cloud.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
                wait=True,
            )

        print(f"Successfully migrated {len(batch)} points.")

        print(
            "Final cloud count:",
            cloud.get_collection(COLLECTION_NAME).points_count,
        )

    finally:
        local.close()


if __name__ == "__main__":
    main()
