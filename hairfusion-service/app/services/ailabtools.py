import io
import uuid
from pathlib import Path
from typing import Dict, Any, Iterable, Tuple

import httpx
from PIL import Image

from app.settings import settings

OUT_DIR = Path("outputs"); OUT_DIR.mkdir(exist_ok=True)

class AILabError(Exception): ...
class AILabAuthError(AILabError): ...
class AILabBadReq(AILabError): ...

def _header_variants(api_key: str) -> Iterable[Dict[str, str]]:
    # 여러 서비스가 서로 다른 키 이름을 요구하므로 모두 시도
    bearer = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    x1 = {"X-API-Key": api_key, "Accept": "application/json"}
    x2 = {"X-API-KEY": api_key, "Accept": "application/json"}
    # 우선순위: X-API-Key 계열을 먼저 시도해보자 (로그상 Authorization은 실패)
    return (x1, x2, bearer)

def _payload_variants(face_url: str, hair_style: str|None, color: str|None,
                      image_size: int|None, task_type: str|None) -> Iterable[Tuple[str, Dict[str, Any]]]:
    # 다양한 필드명을 커버
    yield ("json", {
        "face_url": face_url,
        "hair_style": hair_style,
        "color": color,
        "image_size": image_size,
        "task_type": task_type,
    })
    yield ("json", {
        "image_url": face_url,
        "hairstyle": hair_style,
        "color": color,
        "size": image_size,
        "mode": task_type,
    })
    yield ("json", {k: v for k, v in {
        "image_url": face_url, "face_url": face_url,
        "hairstyle": hair_style, "hair_style": hair_style,
        "color": color, "size": image_size, "image_size": image_size,
        "mode": task_type, "task_type": task_type,
    }.items() if v not in (None, "", [])})
    yield ("form", {k: v for k, v in {
        "image_url": face_url, "hairstyle": hair_style,
        "color": color, "size": image_size, "mode": task_type,
    }.items() if v not in (None, "", [])})

async def hairstyle_edit_pro(
    face_url: str,
    hair_style: str | None = None,
    color: str | None = None,
    image_size: int | None = None,
    task_type: str | None = None,
) -> str:
    """
    AILabTools 헤어스타일 체인저(Pro) 호출.
    - 여러 엔드포인트/헤더/페이로드 조합을 자동 시도.
    - 성공 시 로컬 PNG 경로 반환.
    """

    if not settings.ailab_api_key:
        # 드라이런: 키 없으면 파이프라인만 점검
        fname = OUT_DIR / f"dryrun_{uuid.uuid4().hex}.png"
        Image.new("RGB", (1, 1), (0, 0, 0)).save(fname)
        return str(fname)

    last_errors: list[str] = []
    timeout = httpx.Timeout(180)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for base in settings.ailab_base_urls:
            base = base.rstrip("/")
            print(f">>> TRY AILAB URL: {base}")
            for headers in _header_variants(settings.ailab_api_key):
                for mode, payload in _payload_variants(face_url, hair_style, color, image_size, task_type):
                    try:
                        if mode == "json":
                            resp = await client.post(base, json=payload, headers=headers)
                        else:
                            resp = await client.post(base, data=payload, headers=headers)

                        ctype = resp.headers.get("Content-Type", "")
                        status = resp.status_code
                        previewable = ("application/json" in ctype) or ("text" in ctype)
                        text_preview = resp.text[:300] if previewable else f"[{ctype} {len(resp.content)} bytes]"
                        print(f"--- TRY headers={list(headers.keys())}, mode={mode}, status={status}, ctype={ctype}, resp={text_preview}")

                        # 401이어도 다음 헤더/페이로드/엔드포인트를 계속 시도해야 함
                        if status == 401:
                            last_errors.append(f"{base} -> 401 Unauthorized (headers={list(headers.keys())})")
                            continue
                        if status == 404:
                            last_errors.append(f"{base} -> 404 Not Found")
                            continue
                        if status >= 400:
                            last_errors.append(f"{base} -> {status}: {text_preview}")
                            continue

                        # 성공 응답 처리
                        if "image/" in ctype:
                            fname = OUT_DIR / f"result_{uuid.uuid4().hex}.png"
                            Image.open(io.BytesIO(resp.content)).save(fname)
                            return str(fname)

                        # JSON 안에 이미지 URL이 있는 경우
                        data = None
                        try:
                            data = resp.json()
                        except Exception:
                            pass

                        if isinstance(data, dict):
                            for k in ("result_url", "image_url", "output_url", "url"):
                                if isinstance(data.get(k), str):
                                    img_url = data[k]
                                    img = await client.get(img_url)
                                    img.raise_for_status()
                                    fname = OUT_DIR / f"result_{uuid.uuid4().hex}.png"
                                    Image.open(io.BytesIO(img.content)).save(fname)
                                    return str(fname)

                            last_errors.append(f"{base} -> 200 but no image/url field: keys={list(data.keys())}")
                            continue

                        last_errors.append(f"{base} -> 200 but unknown format: ctype={ctype}")
                        continue

                    except httpx.RequestError as e:
                        last_errors.append(f"{base} -> network error: {e}")
                        continue
                    except Exception as e:
                        last_errors.append(f"{base} -> unexpected: {e}")
                        continue

    raise AILabError("All candidates failed.\n" + "\n".join(last_errors[-8:]))
