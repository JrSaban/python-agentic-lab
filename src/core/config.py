from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings
    Équivalent conceptuel de config/*.php et du .env dans Laravel.
    Les variables d'environnement sont strictement typées et validées au démarrage.
    """

    APP_NAME: str = "Todo API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Configuration PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Refresh Token
    REFRESH_TOKEN_EXPIRE_DAYS: int

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if v.startswith("change-me") or len(v.encode()) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 bytes and must not be the "
                "'change-me' placeholder"
            )
        return v

    # URL de connexion directe (optionnelle, surchargée par Docker Compose)
    DATABASE_URL: str | None = None

    @computed_field  # Champ calculé automatiquement si DATABASE_URL n'est pas explicite
    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
