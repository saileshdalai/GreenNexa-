"""
GreenNexa — Test Fixtures (conftest.py)

Provides SQLite in-memory database session with StaticPool, FastAPI test client,
and pre-populated organisation and sensor data fixtures.
"""

import os
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force SQLite in-memory for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")

import app.db.database as db_mod
from app.db.database import Base
from app.db.models import Organisation

# StaticPool ensures a single connection is maintained for in-memory SQLite across sessions
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database module globals BEFORE importing app.main
db_mod.engine = engine
db_mod.SessionLocal = TestingSessionLocal

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional SQLAlchemy database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with db dependency overridden."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db_mod.get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_orgs(db_session: Session) -> dict[str, Organisation]:
    """Seed two distinct organisations for isolation testing."""
    org1 = Organisation(
        id="ORG-TEST-A",
        name="Test College A",
        org_type="college",
        location="Campus Alpha",
    )
    org2 = Organisation(
        id="ORG-TEST-B",
        name="Test Hospital B",
        org_type="hospital",
        location="Building Beta",
    )
    db_session.add_all([org1, org2])
    db_session.commit()
    return {"org_a": org1, "org_b": org2}


@pytest.fixture
def auth_headers(db_session: Session):
    """Provide a helper function to create test users and return Bearer auth headers."""
    from app.core.security import create_access_token, hash_password
    from app.db.models import User

    def _make_headers(email: str, role: str, organisation_id: str = "ORG-TEST-A") -> dict[str, str]:
        user = db_session.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password("Password123!"),
                full_name=f"Test {role}",
                role=role,
                organisation_id=organisation_id,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        token = create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "role": user.role,
                "organisation_id": user.organisation_id,
            }
        )
        return {"Authorization": f"Bearer {token}"}

    return _make_headers
