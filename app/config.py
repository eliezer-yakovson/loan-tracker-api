from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # JWT
    secret_key: str = "change-this-secret-key-in-production"
    token_expire_days: int = 7

    # CORS
    frontend_origin: str = ""  # e.g. https://loan-tracker.vercel.app

    # SMTP (email for OTP codes)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "מעקב הלוואות"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
