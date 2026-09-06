from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/commercial_ai"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    GENERAL_MODEL: str = "gemma4:12b-mlx"
    HEAVY_MODEL: str = "gemma4:26b-mlx"
    CODING_MODEL: str = "qwen3-coder:30b"
    REASONING_MODEL: str = "deepseek-r1:32b"
    VISION_MODEL: str = "qwen3-vl:8b"
    FAST_MODEL: str = "qwen3:8b"
    
    OPENROUTER_API_KEY: Optional[str] = None
    
    LLM_PROVIDER: str = "ollama" # "ollama" or "groq"
    GROQ_API_KEY: Optional[str] = None
    # Production Groq models; the developer/free tier remains rate-limited.
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_FAST_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_REASONING_EFFORT: str = "high"
    GROQ_JSON_REASONING_EFFORT: str = "none"
    GROQ_MAX_COMPLETION_TOKENS: int = 2048
    
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    JWT_SECRET: str = "your_jwt_secret_here"
    FRONTEND_URL: str = "http://localhost:5175"
    

    
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    ALLOW_DEBUGGER: bool = False
    ALLOW_ONLINE_LATEX: bool = False
    DATABASE_POOL_SIZE: int = 2
    DATABASE_MAX_OVERFLOW: int = 1
    DATABASE_POOL_TIMEOUT: int = 10
    LANGGRAPH_POOL_SIZE: int = 2

    class Config:
        env_file = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), ".env")
        env_file_encoding = 'utf-8'

# Load local defaults without overriding variables supplied by the runtime.  This
# lets CI, Docker and Vercel inject their own configuration safely.
from dotenv import load_dotenv
import os
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path, override=False)

import logging
import secrets

settings = Settings(
    OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", None),
    LLM_PROVIDER=os.getenv("LLM_PROVIDER", "ollama"),
    GROQ_API_KEY=os.getenv("GROQ_API_KEY", None),
    GROQ_MODEL=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
    GROQ_FAST_MODEL=os.getenv("GROQ_FAST_MODEL", "qwen/qwen3.8-27b"),
    GROQ_REASONING_EFFORT=os.getenv("GROQ_REASONING_EFFORT", "high"),
    GROQ_JSON_REASONING_EFFORT=os.getenv("GROQ_JSON_REASONING_EFFORT", "none"),
    GROQ_MAX_COMPLETION_TOKENS=int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "2048")),
    GENERAL_MODEL=os.getenv("GENERAL_MODEL", "gemma4:12b-mlx"),
    HEAVY_MODEL=os.getenv("HEAVY_MODEL", "gemma4:12b-mlx"),
    REASONING_MODEL=os.getenv("REASONING_MODEL", "gemma4:12b-mlx"),
    CODING_MODEL=os.getenv("CODING_MODEL", "qwen3:14b"),
    VISION_MODEL=os.getenv("VISION_MODEL", "qwen3:14b"),
    FAST_MODEL=os.getenv("FAST_MODEL", "qwen3:14b")
)

# Ensure JWT secret is of sufficient length. In production, fail fast.
if getattr(settings, "JWT_SECRET", None) is None:
    raise RuntimeError("JWT_SECRET must be set in environment or .env")

if len(settings.JWT_SECRET) < 32:
    if settings.APP_ENV == "production":
        raise RuntimeError("Insecure JWT_SECRET in production: must be at least 32 bytes. Set a secure JWT_SECRET env var.")
    # For non-production, generate an ephemeral secure secret to avoid short-key warnings
    ephemeral = secrets.token_hex(32)
    logging.getLogger(__name__).warning(
        "Configured JWT_SECRET is shorter than 32 bytes. Generating an ephemeral secure JWT secret for this process."
    )
    settings.JWT_SECRET = ephemeral


def cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
