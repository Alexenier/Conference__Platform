from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def create_first_admin():
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.models.user_role import UserRole
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.admin_email).first()
        if not existing:
            admin = User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                full_name=settings.admin_full_name,
            )
            db.add(admin)
            db.flush()
            db.add(UserRole(user_id=admin.id, role_id=3))
            db.commit()
            print(f"[startup] Адмін створений: {settings.admin_email}")
        else:
            print(f"[startup] Адмін вже існує: {settings.admin_email}")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}