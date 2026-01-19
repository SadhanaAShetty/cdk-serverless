from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    DATABASE_URL: str = "sqlite:///./homeswap.db"
    
    # Application
    REPORTS_DIR: str = "house_pictures"
    
    # AWS SES
    AWS_ACCOUNT_ID: Optional[str] = None
    AWS_REGION: Optional[str] = "eu-west-1"
    SES_SENDER_EMAIL: Optional[str] = None
    
    # AWS S3
    S3_BUCKET_NAME: Optional[str] = "home-image-bucket-777"
    PRESIGNED_URL_EXPIRATION: int = 3600 
    AWS_PROFILE: Optional[str] = None  
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "fallback-secret-for-dev-only"  
    
    class Config:
        env_file = "../.env" 


settings = Settings()