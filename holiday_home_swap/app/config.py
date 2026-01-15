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
    
    # AWS S3
    S3_BUCKET_NAME: Optional[str] = "home-image-bucket"
    PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour in seconds
    
    class Config:
        env_file = ".env"


settings = Settings()