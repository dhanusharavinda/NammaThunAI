from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
_ENV_PATH = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # Load backend/.env regardless of current working directory.
    model_config = SettingsConfigDict(env_file=str(_ENV_PATH), env_file_encoding="utf-8")

    openai_api_key: str
    openai_chat_model: str = "gpt-4o"
    openai_stt_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"

    # Optional: OCR helpers (Windows-friendly).
    # - TESSERACT_CMD example: C:\Program Files\Tesseract-OCR\tesseract.exe
    # - POPPLER_PATH example: C:\Program Files\poppler\Library\bin
    tesseract_cmd: str | None = None
    poppler_path: str | None = None

    # Deployment safety limits
    max_input_chars: int = 2000
    rate_limit_per_minute: int = 5
    followup_limit: int = 5

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"


settings = Settings()  # type: ignore[call-arg]

