from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 프로젝트 루트

class Settings(BaseSettings):
    # hairfusion-service (내부 호출용)
    hairfusion_base_url: str = Field(default="http://127.0.0.1:8100", alias="HAIRFUSION_BASE_URL")
    request_timeout: int = Field(default=180, alias="REQUEST_TIMEOUT")

    # (주의) AILab 관련 설정은 백엔드에서는 쓰지 않음!
    # ailab_base_url(s) 같은 필드 정의 금지

    class Config:
        env_file = str(ROOT / ".env")
        extra = "ignore"

settings = Settings()
