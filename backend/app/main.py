from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base, SessionLocal
from .routers import auth, institutions, fdrs, verification, risk, maturity, releases, dashboard, copilot, admin
from .services.maturity import run_maturity_scan

app = FastAPI(
    title="FDRSETU — AICTE FDR & Security Deposit Portal",
    description="Fixed Deposit Registration, Evaluation, Security & Tracking Utility. "
                "SIH 2026 prototype — all data DEMO / SYNTHETIC.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, institutions.router, fdrs.router, verification.router,
          risk.router, maturity.router, releases.router, dashboard.router,
          copilot.router, admin.router):
    app.include_router(r, prefix="/api")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    if settings.SEED_DEMO:
        from .seed import seed
        if seed():
            print("Seeded DEMO/SYNTHETIC dataset")
    db = SessionLocal()
    try:
        run_maturity_scan(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FDRSETU", "data": "DEMO / SYNTHETIC"}
