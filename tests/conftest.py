import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Створюємо ролі
        for role_id, role_name in [(1, "participant"), (2, "org_committee"), (3, "admin")]:
            if not db.query(Role).filter(Role.id == role_id).first():
                db.add(Role(id=role_id, name=role_name))
        db.commit()

        # Створюємо адміна
        if not db.query(User).filter(User.email == "admin@test.com").first():
            admin = User(email="admin@test.com", password_hash=hash_password("admin123"), full_name="Admin")
            db.add(admin)
            db.flush()
            db.add(UserRole(user_id=admin.id, role_id=3))
            db.commit()

        # Створюємо учасника
        if not db.query(User).filter(User.email == "participant@test.com").first():
            participant = User(email="participant@test.com", password_hash=hash_password("pass123"), full_name="Participant")
            db.add(participant)
            db.flush()
            db.add(UserRole(user_id=participant.id, role_id=1))
            db.commit()

        # Створюємо орг. комітет
        if not db.query(User).filter(User.email == "org@test.com").first():
            org = User(email="org@test.com", password_hash=hash_password("pass123"), full_name="Org")
            db.add(org)
            db.flush()
            db.add(UserRole(user_id=org.id, role_id=2))
            db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def admin_token(client):
    response = client.post("/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def participant_token(client):
    response = client.post("/auth/login", json={"email": "participant@test.com", "password": "pass123"})
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def org_token(client):
    response = client.post("/auth/login", json={"email": "org@test.com", "password": "pass123"})
    return response.json()["access_token"]