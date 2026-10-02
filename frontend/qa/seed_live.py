"""Ephemeral CI-only browser fixtures. Never changes deployed backend configuration."""
import json
import os
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.identity import Organization, User
from app.seed_demo import seed_demo_data

if os.environ.get("CI") != "true" or settings.DB_NAME != "agrochain_browser_test":
    raise RuntimeError("Only the ephemeral agrochain_browser_test CI database is allowed")

seed_demo_data()  # Existing allowlist users keep their discarded random ordinary passwords.
password = token_urlsafe(36)
email = f"browser-{uuid4().hex}@example.com"
engine = create_engine(settings.MIGRATION_DATABASE_URL)
with Session(engine) as session:
    organization = Organization(name="Browser QA isolated organization", organization_type="farm", is_active=True)
    session.add(organization)
    session.flush()
    session.add(User(organization_id=organization.id, role_code="grower", email=email,
                     full_name="Browser QA credential user", password_hash=hash_password(password),
                     failed_login_attempts=0, is_active=True))
    session.commit()
engine.dispose()
path = Path(__file__).with_name(".live-credentials.json")
path.write_text(json.dumps({"email": email, "password": password}))
path.chmod(0o600)
print("Ephemeral browser fixtures created; credentials are not logged or uploaded.")
