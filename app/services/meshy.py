from __future__ import annotations
import io
import json
import time
from pathlib import Path
from typing import Dict, Any

import httpx
from PIL import Image

from app.settings import settings

OUT_DIR = Path("outputs/meshy")
OUT_DIR.mkdir(parents=True, exist_ok=True)


class MeshyError(Exception):
    ...


class MeshyAuthError(MeshyError):
    ...


class MeshyBadReq(MeshyError):
    ...


class MeshyTimeout(MeshyError):
    ...


def _pick_job_id(data: Dict[str, Any]) -> str:
    for k in ("result", "job_id", "id", "task_id", "taskId"):
        if k in data and data[k]:
            return str(data[k])
    raise MeshyError(f"unexpected create-response: {json.dumps(data)[:400]}")


async def create_image_to_3d(image_url: str) -> str:
    """
    Meshy Image-to-3D 작업 생성 (최종 고퀄리티 옵션 적용)
    """

    base = (settings.meshy_base_url or "https://api.meshy.ai").rstrip("/")
    url = base + "/openapi/v1/image-to-3d"

    if not settings.meshy_api_key:
        raise MeshyAuthError("no API key")

    headers = {
        "Authorization": f"Bearer {settings.meshy_api_key}",
        "Content-Type": "application/json",
    }

    # ----------------------------
    # 🔥 고품질 옵션 최종 조합
    # ----------------------------
    payload: Dict[str, Any] = {
        "image_url": image_url,

        # 최신 모델 사용 (meshify-6 preview로 매핑)
        "ai_model": "latest",

        # 텍스처 + PBR 풀 세팅
        "should_texture": True,
        "enable_pbr": True,

        # ⭐ highest-precision → should_remesh = False
        #   (리메시 True면 polycount 맞추려고 디테일 손실 발생)
        "should_remesh": False,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=60)

        if r.status_code == 401:
            raise MeshyAuthError(r.text)
        if r.status_code == 400:
            raise MeshyBadReq(r.text)
        r.raise_for_status()

        data = r.json()
        return _pick_job_id(data)


async def get_job(task_id: str) -> Dict[str, Any]:
    base = (settings.meshy_base_url or "https://api.meshy.ai").rstrip("/")
    url = base + f"/openapi/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {settings.meshy_api_key}"}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=60)

        if r.status_code == 401:
            raise MeshyAuthError(r.text)

        r.raise_for_status()
        return r.json()


async def wait_and_download(task_id: str) -> Path:
    """
    Meshy 작업 SUCCEEDED까지 대기 후 GLB 다운로드
    """
    deadline = time.time() + (settings.meshy_timeout or 600)
    last: Dict[str, Any] = {}

    while time.time() < deadline:
        last = await get_job(task_id)
        st = (last.get("status") or "").upper()

        if st == "SUCCEEDED":
            model_url = last.get("model_url")
            if not model_url:
                raise MeshyError(f"no model_url in {last}")

            async with httpx.AsyncClient() as client:
                r = await client.get(model_url, timeout=120)
                r.raise_for_status()

                fname = OUT_DIR / f"meshy_{task_id.replace('-', '')[:16]}.glb"
                with open(fname, "wb") as f:
                    f.write(r.content)

                return fname

        elif st in ("FAILED", "CANCELED"):
            raise MeshyError(f"job failed: {last}")

        time.sleep(3)

    raise MeshyTimeout(f"job timeout: {task_id}")
