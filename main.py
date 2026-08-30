import threading
import time
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import engine, Base, SessionLocal
from app.api.v1.router import api_v1_router
from app.services.tool_registry import ToolRegistry
from app.services.scheduler_service import SchedulerService
from app.runtime.worker import WorkerEngine
import app.models # Ensure all ORM models are loaded into Base.metadata

logger = logging.getLogger(__name__)

# Global flag for background threads
running_flag = True

def background_worker_loop():
    worker = WorkerEngine(worker_id="embedded-worker")
    logger.info("Embedded background worker thread started.")
    while running_flag:
        db = SessionLocal()
        try:
            processed = worker.process_one_message(db)
            if not processed:
                time.sleep(1.0)
        except Exception as e:
            logger.error(f"Embedded worker error: {e}")
            time.sleep(2.0)
        finally:
            db.close()

def background_scheduler_loop():
    logger.info("Embedded scheduler thread started.")
    while running_flag:
        db = SessionLocal()
        try:
            scheduler = SchedulerService(db)
            scheduler.evaluate_schedules()
        except Exception as e:
            logger.error(f"Embedded scheduler error: {e}")
        finally:
            db.close()
        time.sleep(10.0) # Evaluate schedules every 10 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    global running_flag
    running_flag = True
    
    # 1. Initialize DB tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Register builtin safe tools into DB registry
    db = SessionLocal()
    try:
        tool_registry = ToolRegistry(db)
        tool_registry.register_builtin_tools()
    finally:
        db.close()
        
    # 3. Start embedded background worker thread
    worker_thread = threading.Thread(target=background_worker_loop, daemon=True)
    worker_thread.start()

    # 4. Start embedded scheduler thread
    scheduler_thread = threading.Thread(target=background_scheduler_loop, daemon=True)
    scheduler_thread.start()

    yield

    running_flag = False

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