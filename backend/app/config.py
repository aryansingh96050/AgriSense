import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AgriSense"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./agrisense.db"
    
    # API Prefix
    API_V1_PREFIX: str = "/api/v1"
    
    # Safety Limits for Actuators
    MAX_CONTINUOUS_PUMP_MINUTES: int = 45
    DEFAULT_SOIL_MOISTURE_TARGET: float = 65.0
    DEFAULT_WILTING_POINT: float = 30.0
    
    # Weather Location
    DEFAULT_LATITUDE: float = 28.6139
    DEFAULT_LONGITUDE: float = 77.2090
    USE_REAL_WEATHER_API: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
