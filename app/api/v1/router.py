from fastapi import APIRouter
from app.api.v1.settings import router as settings_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.projects import router as projects_router
from app.api.v1.agents import router as agents_router
from app.api.v1.memory import router as memory_router
from app.api.v1.tools import router as tools_router
from app.api.v1.executions import router as executions_router

api_v1_router = APIRouter()
api_v1_router.include_router(settings_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(executions_router)
