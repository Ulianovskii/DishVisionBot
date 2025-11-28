from pydantic import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    openai_api_key: str

    default_language: str = "ru"
    log_level: str = "INFO"
    api_timeout: int = 30
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    database_url: str
    admin_user_ids: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
