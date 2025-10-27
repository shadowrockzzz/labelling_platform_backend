from pydantic_settings import BaseSettings
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "LabelBox Clone API"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    SECRET_KEY: str
    TOKEN_PROVIDER: str = "simple"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    class Config:
        env_file = "../.env"

    @property
    def db_url(self):
        return self.DATABASE_URL or f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

settings = Settings()
print(settings.dict())
print(settings.db_url)
