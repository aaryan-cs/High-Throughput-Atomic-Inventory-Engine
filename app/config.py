from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql+asyncpg://flash:flash@localhost:5432/flashsale"
    mlflow_tracking_uri: str = "http://localhost:5000"

    sale_item_id: str = "jersey-2026-ltd"
    sale_initial_stock: int = 100

    worker_batch_size: int = 200
    worker_interval_ms: int = 50

    fraud_ip_velocity_window_sec: int = 10
    fraud_ip_velocity_max: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
