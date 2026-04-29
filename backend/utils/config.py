# Yeh file .env se saari settings load karti hai.
# Agar koi key missing ho toh startup pe hi error aata hai — runtime pe nahi.
# Har jagah se settings yahan se import karo, hardcode bilkul mat karo.

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Repo root se .env load karo
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


class Settings(BaseSettings):
    """Central config — saari .env values yahan milti hain."""

    # --- Groq LLM ---
    groq_api_key: str = Field(..., validation_alias="GROQ_API_KEY")
    groq_model: str = Field("llama-3.1-8b-instant", validation_alias="GROQ_MODEL")

    # --- FastAPI ---
    app_host: str = Field("0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(8000, validation_alias="APP_PORT")
    debug: bool = Field(False, validation_alias="DEBUG")

    # --- SQLite ---
    database_url: str = Field(
        f"sqlite:///{_ROOT}/data/db.sqlite3", validation_alias="DATABASE_URL"
    )

    # --- ChromaDB ---
    chroma_persist_dir: str = Field(
        str(_ROOT / "data" / "chroma"), validation_alias="CHROMA_PERSIST_DIR"
    )

    # --- MLflow ---
    mlflow_tracking_uri: str = Field(
        str(_ROOT / "data" / "mlruns"), validation_alias="MLFLOW_TRACKING_URI"
    )
    mlflow_experiment_name: str = Field(
        "cv-interview-coach", validation_alias="MLFLOW_EXPERIMENT_NAME"
    )

    # --- LiveKit ---
    livekit_url: Optional[str] = Field(None, validation_alias="LIVEKIT_URL")
    livekit_api_key: Optional[str] = Field(None, validation_alias="LIVEKIT_API_KEY")
    livekit_api_secret: Optional[str] = Field(
        None, validation_alias="LIVEKIT_API_SECRET"
    )

    # --- Agent tuning ---
    max_retries: int = Field(3, validation_alias="MAX_RETRIES")
    agent_timeout_seconds: int = Field(60, validation_alias="AGENT_TIMEOUT_SECONDS")

    @field_validator("groq_api_key")
    @classmethod
    def _groq_key_not_empty(cls, v: str) -> str:
        """Blank key se bilkul kaam nahi chalega."""
        if not v or v.strip() == "":
            raise ValueError("GROQ_API_KEY .env mein set karo — blank nahi chalega")
        return v.strip()

    model_config = {"env_file": str(_ROOT / ".env"), "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton — ek baar load, baar baar reuse."""
    return Settings()
