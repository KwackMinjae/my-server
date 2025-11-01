# app/settings.py
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    # 단일 값만 .env에서 읽음
    ailab_base_url: str = Field(
        default="https://www.ailabapi.com/api/portrait/effects/hairstyle-changer-pro",
        alias="AILAB_BASE_URL"
    )
    ailab_api_key: str = Field(default="", alias="AILAB_API_KEY")
    request_timeout: int = Field(default=180, alias="REQUEST_TIMEOUT")

    def effective_ailab_urls(self) -> list[str]:
        base = self.ailab_base_url.rstrip("/")

        # 확실한 후보만 명시적으로 나열 (중복/오타 방지)
        candidates = [
            base,  # .env에 적은 값 그대로
            "https://www.ailabapi.com/api/portrait/hairstyle-editor-pro",
            "https://www.ailabapi.com/api/portrait/effects/hairstyle-editor-pro",
            "https://www.ailabapi.com/api/portrait/effects/hairstyle_changer_pro",
            "https://www.ailabapi.com/api/portrait/effects/hairstyle-changer-pro",
        ]

        out, seen = [], set()
        for c in candidates:
            c = c.rstrip("/")
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out

settings = Settings()
