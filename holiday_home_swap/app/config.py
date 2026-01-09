from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    DATABASE_URL: str = "sqlite:///./homeswap.db"
    
    # Application
    REPORTS_DIR: str = "house_pictures"
    
    class Config:
        env_file = ".env"


settings = Settings()