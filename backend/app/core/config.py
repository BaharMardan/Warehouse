from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    secret_key: str
    access_token_expire_minutes: int = 480


settings = Settings()