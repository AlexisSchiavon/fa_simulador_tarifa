import os

from pydantic_settings import BaseSettings, SettingsConfigDict

PORT = int(os.getenv("PORT", 8000))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Hyperred FA Sandbox"
    app_env: str = "development"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/hyperred.db")
    log_level: str = "INFO"
    timezone: str = "America/Mexico_City"
    port: int = PORT

    # Capacidad estándar de autobús FA
    bus_capacity: int = 45

    # Límites tarifarios del algoritmo híbrido
    price_floor_multiplier: float = 0.65
    price_ceiling_multiplier: float = 3.50


settings = Settings()
