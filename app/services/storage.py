import mimetypes
import uuid
from pathlib import Path
from typing import Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.settings import settings


class StorageError(Exception):
    pass


def _s3_client():
    try:
        return boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
    except Exception as e:
        raise StorageError(f"Failed to init S3 client: {e}")


def _guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    return ctype or "application/octet-stream"


def public_url(bucket: str, key: str) -> str:
    # 단순 퍼블릭 URL (정적 퍼블릭 버킷 전제)
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def upload_file(local_path: str, key_prefix: str = "results/") -> Tuple[str, str]:
    """
    파일을 S3 버킷에 업로드하고 (public-read) (key, url) 을 반환
    """
    if not settings.s3_bucket:
        raise StorageError("S3_BUCKET not configured")

    path = Path(local_path)
    if not path.exists():
        raise StorageError(f"Local file not found: {local_path}")

    key = f"{key_prefix}{uuid.uuid4().hex}{path.suffix.lower()}"
    client = _s3_client()

    extra_args = {
        "ACL": "public-read",
        "ContentType": _guess_content_type(path),
        "CacheControl": "public, max-age=31536000",
    }

    try:
        client.upload_file(
            Filename=str(path),
            Bucket=settings.s3_bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
    except (BotoCoreError, ClientError) as e:
        raise StorageError(f"S3 upload failed: {e}")

    return key, public_url(settings.s3_bucket, key)
