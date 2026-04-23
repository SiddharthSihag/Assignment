from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from src.database import Base, engine
from src.routers.auth_router import router as auth_router
from src.routers.batches import router as batches_router
from src.routers.sessions import router as sessions_router
from src.routers.attendance import router as attendance_router
from src.routers.summary import router as summary_router
from src.routers.monitoring import router as monitoring_router
# Create all tables on startup (safe to call multiple times)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillBridge Attendance API",
    description="Attendance management system for the SkillBridge skilling programme.",
    version="1.0.0",
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(batches_router)
app.include_router(sessions_router)
app.include_router(attendance_router)
app.include_router(summary_router)
app.include_router(monitoring_router)


# ─── Global error handlers ───────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Return 422 with a descriptive body instead of the raw Pydantic dump."""
    errors = []
    for e in exc.errors():
        field = " → ".join(str(loc) for loc in e["loc"])
        errors.append({"field": field, "message": e["msg"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed.", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Catch FK violations and duplicate key errors.
    Return 404 for FK violations (referenced entity not found),
    409 for unique constraint violations.
    """
    msg = str(exc.orig).lower()
    if "foreign key" in msg or "violates foreign key" in msg:
        return JSONResponse(
            status_code=404,
            content={"detail": "Referenced resource not found (foreign key violation)."},
        )
    if "unique" in msg or "duplicate" in msg:
        return JSONResponse(
            status_code=409,
            content={"detail": "A record with these values already exists."},
        )
    return JSONResponse(
        status_code=400,
        content={"detail": "Database constraint violation."},
    )


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "SkillBridge Attendance API"}