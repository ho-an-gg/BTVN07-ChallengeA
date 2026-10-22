"""Cấu hình project: hằng số hiển thị, giới hạn thực thi và settings đọc từ .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

import paths

PROJECT_NAME = "stage-05-memory"
APP_TITLE = "Stage 05: Persistent memory"
CAPABILITY_TEXT = "Tools: read_file, write_file, bash, update_project_memory. Quy ước JSON được nạp đầu session; mọi thay đổi ghi log timestamp và before/after."

# Giới hạn số lần gọi model trong một lượt chat (ModelCallLimitMiddleware).
MODEL_CALL_LIMIT = 8
# Giới hạn số tool calls trong một lượt chat (ToolCallLimitMiddleware).
TOOL_CALL_LIMIT = 20
# Giới hạn số bước của LangGraph (recursion limit), không phải số tool calls.
RECURSION_LIMIT = 50


@dataclass(frozen=True)
class Settings:
    api_key: str
    model_name: str
    base_url: str | None
    provider: str = "openai"


def load_settings() -> tuple[Settings | None, list[str]]:
    """Đọc .env của project này. Trả (settings, []) hoặc (None, danh sách biến còn thiếu)."""
    load_dotenv(paths.ENV_PATH, override=False)
    model_name = os.getenv("MODEL_NAME", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    provider = os.getenv("MODEL_PROVIDER", "").strip().lower()
    if not provider:
        provider = "google" if base_url and "generativelanguage.googleapis.com" in base_url.lower() else "openai"
    if provider in ("gemini", "google-genai"):
        provider = "google"
    if provider not in ("google", "openai"):
        return None, ["MODEL_PROVIDER phải là google hoặc openai"]
    if provider == "google":
        api_key = (
            os.getenv("GOOGLE_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()  # compat với .env cũ dùng Gemini OpenAI endpoint
        )
        key_name = "GOOGLE_API_KEY"
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        key_name = "OPENAI_API_KEY"
    missing = [name for name, value in ((key_name, api_key), ("MODEL_NAME", model_name)) if not value]
    if missing:
        return None, missing
    return Settings(api_key=api_key, model_name=model_name, base_url=base_url, provider=provider), []
