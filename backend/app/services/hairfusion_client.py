import httpx
from pydantic import HttpUrl
from typing import Optional, Dict, Any
from app.settings import settings

class HairFusionError(Exception):
    pass

async def fuse_hair(
    face_url: str | HttpUrl,
    hair_style: Optional[str] = None,
    color: Optional[str] = None,
    image_size: Optional[int] = None,
    task_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    hair_backend -> hairfusion-service(/fuse) 로 프록시 호출
    """
    url = settings.hairfusion_base_url.rstrip("/") + "/fuse"

    payload: Dict[str, Any] = {
        "face_url": str(face_url),
    }
    if hair_style is not None:
        payload["hair_style"] = hair_style
    if color is not None:
        payload["color"] = color
    if image_size is not None:
        payload["image_size"] = image_size
    if task_type is not None:
        payload["task_type"] = task_type

    timeout = settings.request_timeout

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(url, json=payload)
        except Exception as e:
            raise HairFusionError(f"Connect error to hairfusion-service: {e!r}")

        if r.status_code >= 400:
            # hairfusion-service의 에러 메시지 전달
            raise HairFusionError(f"backend error {r.status_code}: {r.text}")

        try:
            return r.json()
        except Exception:
            return {"status": "ok", "raw": r.text}
