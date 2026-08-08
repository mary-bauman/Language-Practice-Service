from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from app.observability import RequestContextMiddleware, configure_logging, metrics_response
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.items import router as items_router
from app.api.practice import router as practice_router
from app.api.scheduler import router as scheduler_router
from app.api.import_export import router as import_export_router

configure_logging()
app = FastAPI(title="Language Practice Service")
app.add_middleware(RequestContextMiddleware)

app.include_router(health_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(items_router, prefix="/api/v1")
app.include_router(practice_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(import_export_router, prefix="/api/v1")

@app.get("/metrics", tags=["observability"], response_class=PlainTextResponse)
async def metrics():
    return await metrics_response()

@app.get("/", tags=["root"])
async def root():
    return {"message": "Language Practice Service - backend is running"}
