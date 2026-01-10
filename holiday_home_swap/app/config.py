from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    DATABASE_URL: str = "sqlite:///./homeswap.db"
    
    # Application
    REPORTS_DIR: str = "house_pictures"
    
    # AWS SES
    AWS_REGION: Optional[str] = "eu-west-1"
    SES_SENDER_EMAIL: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()