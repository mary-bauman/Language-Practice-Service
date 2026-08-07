from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "language-practice-service"
    jwt_audience: str = "language-practice-client"
    expose_reset_tokens: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
