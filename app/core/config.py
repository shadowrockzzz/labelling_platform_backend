from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "LabelBox Clone API"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str = "postgres"
    DATABASE_URL: str | None = None

    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    TOKEN_PROVIDER: str = "jwt"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes as per requirements
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7    # 7 days as per requirements
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DEBUG: bool = True

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5174", "http://localhost:5173", "http://localhost:5175"]

    # AWS S3 settings
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""
    AWS_S3_ENDPOINT: str = ""  # For S3-compatible services (e.g., MinIO)

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")

    @property
    def db_url(self):
        return self.DATABASE_URL or f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

settings = Settings()