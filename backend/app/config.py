import os
from typing import List

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AgriSense")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agrisense.db")
    
    # API Prefix
    API_V1_PREFIX: str = "/api/v1"
    
    # Safety Limits for Actuators
    MAX_CONTINUOUS_PUMP_MINUTES: int = int(os.getenv("MAX_CONTINUOUS_PUMP_MINUTES", 45))
    DEFAULT_SOIL_MOISTURE_TARGET: float = float(os.getenv("DEFAULT_SOIL_MOISTURE_TARGET", 65.0))
    DEFAULT_WILTING_POINT: float = float(os.getenv("DEFAULT_WILTING_POINT", 30.0))
    
    # Weather Location
    DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", 28.6139))
    DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", 77.2090))
    USE_REAL_WEATHER_API: bool = os.getenv("USE_REAL_WEATHER_API", "False").lower() in ("true", "1")
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

settings = Settings()
