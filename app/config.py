from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # JWT — SECRET_KEY must be set explicitly; the app will refuse to start without it.
    secret_key: str
    token_expire_days: int = 7

    # CORS
    frontend_origin: str = ""  # e.g. https://loan-tracker.vercel.app

    # Development mode — set DEBUG=true only locally; never in production
    debug: bool = False

    # Email — Brevo (formerly Sendinblue) HTTP API
    # Sign up free at brevo.com → Settings → API Keys
    brevo_api_key: str = ""
    email_from: str = ""        # verified sender address in Brevo
    email_from_name: str = "מעקב הלוואות"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
