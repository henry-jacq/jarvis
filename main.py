from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import engine, Base, SessionLocal
from app.api.v1.router import api_v1_router
from app.services.tool_registry import ToolRegistry
import app.models # Ensure all ORM models are loaded into Base.metadata

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    
    # Register builtin safe tools into DB registry
    db = SessionLocal()
    try:
        tool_registry = ToolRegistry(db)
        tool_registry.register_builtin_tools()
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Jarvis: Secure, Context-Aware Agent Runtime & Orchestration Platform",
    lifespan=lifespan
)

@app.get("/")
def root():
    return {
        "status": "online",
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)