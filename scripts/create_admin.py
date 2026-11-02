import sys
from pathlib import Path
from getpass import getpass
from getpass import getuser

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Add project root to Python path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables before importing application services.
load_dotenv(PROJECT_ROOT / ".env")

from app.db.database import SessionLocal
from app.models.staff import StaffUserDB
from app.services.auth_service import hash_password


def create_admin():
    db: Session = SessionLocal()

    try:
        print("\n=== SupportIQ AI - Create Admin ===\n")

        existing_admin = (
            db.query(StaffUserDB)
            .filter(StaffUserDB.role == "admin")
            .first()
        )

        if existing_admin:
            print("An admin account already exists.")
            return

        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip()

        if len(username) < 3:
            print("Username must contain at least 3 characters.")
            return

        if "@" not in email or "." not in email:
            print("Please enter a valid email address.")
            return

        if (
            db.query(StaffUserDB)
            .filter(
                (StaffUserDB.username == username)
                | (StaffUserDB.email == email)
            )
            .first()
        ):
            print("Username or email is already registered.")
            return

        password = getpass("Admin password: ")
        confirm_password = getpass("Confirm password: ")

        if len(password) < 8:
            print("Password must contain at least 8 characters.")
            return

        if password != confirm_password:
            print("Passwords do not match.")
            return

        admin = StaffUserDB(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("\nAdmin account created successfully!")

    except Exception:
        db.rollback()
        print("\nCould not create the admin account. Check the backend configuration.")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()