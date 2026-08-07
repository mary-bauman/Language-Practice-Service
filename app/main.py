from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.auth import router as auth_router

app = FastAPI(title="Language Practice Service")

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

@app.get("/", tags=["root"])
async def root():
    return {"message": "Language Practice Service - backend is running"}
