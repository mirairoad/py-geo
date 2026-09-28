from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    host: str = "127.0.0.1"
    port: int = 3001
    debug: bool = False
