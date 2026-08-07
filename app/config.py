from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    class Config:
        env_file = ".env"

settings = Settings()
