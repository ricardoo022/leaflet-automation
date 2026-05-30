from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEAFLETS_", extra="ignore")

    data_dir: Path = Field(default=Path("data"))
    database_path: Path = Field(default=Path("data/leaflets.db"))
    retailer: str = Field(default="lidl")
    request_timeout_seconds: float = Field(default=30.0)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    )


settings = Settings()
