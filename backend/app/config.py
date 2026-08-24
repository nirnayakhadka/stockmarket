from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/nepse_db"
    
    crawl_delay_seconds: float = 2.0
    user_agent: str = "NepseNewsCrawlerBot/1.0 (+mailto:you@example.com)"
    request_timeout_seconds: float = 15.0
    
    enable_scheduler: bool = False
    crawl_schedule_cron_hour: str = "6,12,18"
    
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()