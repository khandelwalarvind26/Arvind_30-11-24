from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    POOL_SIZE: int = 12
    DOWNTIME_OFFSET: int = 5

    class Config:
        env_file = ".env"

settings = Settings()