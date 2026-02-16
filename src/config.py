"""Configuration management for MCP server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    mcp_server_port: int = 8080
    mcp_server_host: str = "0.0.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # API Mode
    use_real_nest_api: bool = False

    # API URLs and Keys
    nest_api_url: str = "http://localhost:8081"
    weather_api_key: str = ""

    # Google Device Access / Nest API Configuration
    google_project_id: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8090/auth/callback"
    google_access_token: str = ""
    google_refresh_token: str = ""

    # GCP Configuration
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"


settings = Settings()
