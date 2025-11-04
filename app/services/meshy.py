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

class MeshyError(Exception): ...
class MeshyAuthError(MeshyError): ...
class MeshyBadReq(MeshyError): ...
class MeshyTimeout(MeshyError): ...

def _pick_job_id(data: Dict[str, Any]) -> str:
    for k in ("result", "job_id", "id", "task_id", "taskId"):
        if k in data and data[k]:
            return str(data[k])
    raise MeshyError(f"unexpected create-response: {json.dumps(data)[:400]}")

async def create_image_to_3d(image_url: str) -> str:
    base = (settings.meshy_base_url or "https://api.meshy.ai").rstrip("/")
    url = base + "/openapi/v1/image-to-3d"
    headers = {
        "Authorization": f"Bearer {settings.meshy_api_key}",
        "Content-Type": "application/json",
    }
    if not settings.meshy_api_key:
        raise MeshyAuthError("no API key")
    payload = {"image_url": image_url}
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
    url  = base + f"/openapi/v1/tasks/{task_id}"
    headers = { "Authorization": f"Bearer {settings.meshy_api_key}" }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=60)
        if r.status_code == 401:
            raise MeshyAuthError(r.text)
        r.raise_for_status()
        return r.json()

async def wait_and_download(task_id: str) -> Path:
    deadline = time.time() + (settings.meshy_timeout or 600)
    last = {}
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
