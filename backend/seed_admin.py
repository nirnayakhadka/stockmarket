"""
seed_admin.py — run once: python seed_admin.py
Creates the first admin user so you can log in and create everyone else
via POST /api/admin/users. Change credentials below or set via env vars.
"""

import os
from app.database import SessionLocal, init_db
from app.models import User, UserRole
from app.services.auth_service import hash_password

USERNAME = os.getenv("ADMIN_USERNAME", "admin")
EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")  # CHANGE THIS


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == USERNAME).first()
        if existing:
            print(f"User '{USERNAME}' already exists (id={existing.id}, role={existing.role.value})")
            return

        user = User(
            username=USERNAME,
            email=EMAIL,
            hashed_password=hash_password(PASSWORD),
            full_name="Administrator",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created admin user '{USERNAME}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()