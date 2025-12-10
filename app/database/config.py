from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    POSTGRES_PASSWORD: str
    POSTGRES_USERNAME: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    model_config = SettingsConfigDict(
        env_file="app/.env",
        env_ignore_empty=True,
        extra="ignore"
    )
    @property
    def POSTGRES_URL(self):
        return f"postgresql://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"



settings = DatabaseSettings()