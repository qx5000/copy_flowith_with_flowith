"""
应用配置文件
管理环境变量和系统配置
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """应用设置"""
    
    # 基础配置
    APP_NAME: str = "AI Agent Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/ai_agent_db"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ChromaDB 配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    
    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LLM_MODEL: str = "llama2:7b"
    
    # OpenAI API 配置（备选）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080"
    ]
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [
        ".pdf", ".txt", ".md", ".docx", ".doc"
    ]
    
    # Agent 配置
    MAX_AGENTS_PER_WORKFLOW: int = 10
    DEFAULT_AGENT_TIMEOUT: int = 300  # 5 分钟
    
    # 工作流配置
    MAX_WORKFLOW_STEPS: int = 100
    WORKFLOW_EXECUTION_TIMEOUT: int = 1800  # 30 分钟
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置实例
settings = Settings()

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
