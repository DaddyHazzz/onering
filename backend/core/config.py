from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development"
    REDIS_URL: str = "redis://localhost:6379/0"
    GROQ_API_KEY: str = ""
    # X/Twitter keys (for dev only; later use Vault)
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"

settings = Settings()
