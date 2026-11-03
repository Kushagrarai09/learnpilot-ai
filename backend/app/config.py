from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LearnPilot AI"
    database_url: str = "sqlite:///./learnpilot.db"
    cors_origins: str = "http://localhost:3000"
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 20
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
