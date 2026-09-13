import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Jarvis Runtime Platform"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/jarvis"
    
    # Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_OLLAMA_MODEL: str = "llama3.2"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Queue & Worker Settings
    REDIS_URL: Optional[str] = None
    WORKER_CONCURRENCY: int = 4
    DEFAULT_MAX_ATTEMPTS: int = 3

    # Workflow & Execution Limits
    MAX_WORKFLOW_DEPTH: int = 3
    MAX_NODES: int = 20
    MAX_PARALLEL_BRANCHES: int = 5

    # Platform
    LOG_LEVEL: str = "INFO"
    DEFAULT_TOKEN_BUDGET: int = 4096
    DEFAULT_EXECUTION_TIMEOUT: int = 300

    model_config = SettingsConfigDict(
        env_file=(ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
