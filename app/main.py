from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="Language Practice Service")

app.include_router(health_router, prefix="/api/v1")

@app.get("/", tags=["root"])
async def root():
    return {"message": "Language Practice Service - backend is running"}
