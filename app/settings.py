<<<<<<< HEAD
﻿# hairfusion-service/app/settings.py
from __future__ import annotations

# pydantic v2 우선, 없으면 v1 폴백
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    V2 = True
except Exception:
    from pydantic import BaseSettings
    V2 = False


class _SettingsV2(BaseSettings):
    # ====== 실제로 사용하는 키 ======
    meshy_api_key: str = ""                          # MESHY_API_KEY
    meshy_base_url: str = "https://api.meshy.ai"     # MESHY_BASE_URL
    request_timeout: float = 180.0                   # 초

    # ====== 남아있는 AILAB 키도 받아두되, 사용은 안 함 ======
    ailab_api_key: str = ""                          # AILAB_API_KEY
    ailab_base_url: str = ""                         # AILAB_BASE_URL

    # .env 자동 로드 + 알 수 없는 키는 허용
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",    # 추가 환경변수 허용
    )


class _SettingsV1(BaseSettings):
    meshy_api_key: str = ""
    meshy_base_url: str = "https://api.meshy.ai"
    request_timeout: float = 180.0
    # 호환용 AILAB 키
    ailab_api_key: str = ""
    ailab_base_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


Settings = _SettingsV2 if V2 else _SettingsV1
=======
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    aws_region: str = Field(..., alias="AWS_REGION")
    aws_s3_bucket: str = Field(..., alias="AWS_S3_BUCKET")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    allowed_origins: str | None = Field(default=None, alias="ALLOWED_ORIGINS")

    class Config:
        env_file = ".env"
        extra = "ignore"

>>>>>>> 37eef4b1704820081e276cb3d2add88a7b0188aa
settings = Settings()
