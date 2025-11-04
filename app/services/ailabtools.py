# hairfusion-service/app/services/ailabtools.py
import io
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple

import httpx
from PIL import Image

from app.settings import settings

OUT_DIR = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)

# ----- 예외 타입
class AILabError(Exception): ...
class AILabAuthError(AILabError): ...
class AILabBadReq(AILabError): ...


def _candidate_headers() -> List[Dict[str, str]]:
    key = settings.ailab_api_key or ""
    return [
        {"ailabapi-api-key": key, "Accept": "application/json"},  # 공식 문서 헤더
        {"X-API-Key": key,       "Accept": "application/json"},  # 호환 시도
        {"X-API-KEY": key,       "Accept": "application/json"},  # 호환 시도
        {"Authorization": f"Bearer {key}", "Accept": "application/json"},  # 호환 시도
    ]



def _candidate_payloads(
    face_url: str, hair_style: str | None, color: str | None,
    image_size: int | None, task_type: str | None
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    (mode, payload) 조합들을 시도.
    - AILab의 실제 파라미터 스펙이 불확실할 수 있어 json/form 두 경로를 모두 지원.
    """
    json_payload = {
        "image_url": face_url,
        "hair_style": hair_style,
        "color": color,
        "image_size": image_size,
        "task_type": task_type,
    }
    # None 값 제거
    json_payload = {k: v for k, v in json_payload.items() if v is not None}

    form_payload = {"image_url": face_url}
    if hair_style:
        form_payload["hair_style"] = hair_style
    if color:
        form_payload["color"] = color
    if image_size:
        form_payload["image_size"] = str(image_size)
    if task_type:
        form_payload["task_type"] = task_type

    return [
        ("json", json_payload),
        ("form", form_payload),
    ]


async def _try_once(client: httpx.AsyncClient, url: str, headers: Dict[str, str],
                    mode: str, payload: Dict[str, Any]) -> str:
    """
    단일 (url, headers, mode, payload) 시도.
    성공 시 결과 이미지를 저장하고 경로 반환.
    """
    if mode == "json":
        r = await client.post(url, json=payload, headers=headers, timeout=settings.request_timeout)
    else:
        r = await client.post(url, data=payload, headers=headers, timeout=settings.request_timeout)

    ctype = r.headers.get("Content-Type", "")
    # 인증/요청 오류 매핑
    if r.status_code == 401:
        raise AILabAuthError(r.text)
    if r.status_code == 400:
        raise AILabBadReq(r.text)
    if r.status_code >= 500:
        raise AILabError(f"Server error {r.status_code}: {r.text}")

    # 바이너리 이미지 바로 내려오는 경우
    if "image/" in ctype:
        fname = OUT_DIR / f"result_{uuid.uuid4().hex}.png"
        Image.open(io.BytesIO(r.content)).save(fname)
        return str(fname)

    # JSON 으로 URL 내려오는 경우
    try:
        data = r.json()
        for k in ("result_url", "image_url", "output_url", "url"):
            if k in data:
                img = await client.get(data[k], timeout=settings.request_timeout)
                img.raise_for_status()
                fname = OUT_DIR / f"result_{uuid.uuid4().hex}.png"
                Image.open(io.BytesIO(img.content)).save(fname)
                return str(fname)
    except Exception:
        pass

    # 예측 불가 포맷
    raise AILabError(f"Unexpected response({r.status_code}, {ctype}): {r.text[:400]}")


async def hairstyle_edit_pro(
    face_url: str,
    hair_style: str | None,
    color: str | None,
    image_size: int | None,
    task_type: str | None
) -> str:
    """
    AILabTools 헤어스타일 체인저(Pro) 호출.
    settings.effective_ailab_urls() 로 후보 엔드포인트를 가져온 다음,
    여러 헤더/페이로드 조합을 순차 시도.
    """
    if not settings.ailab_api_key:
        fname = OUT_DIR / f"dryrun_{uuid.uuid4().hex}.png"
        Image.new("RGB", (1, 1), (0, 0, 0)).save(fname)
        return str(fname)

    candidates = settings.effective_ailab_urls()
    if not candidates:
        raise AILabError("No AILAB base URL configured.")

    # base가 루트일 수 있으므로, 흔히 쓰일 법한 경로 후보를 만들어 함께 시도
    endpoint_suffixes = [
        "/api/hairstyle/edit-pro",
        "/api/hairstyle",
        "/api/hair/fusion",
        "/hairstyle/edit-pro",
        "/fusion/hair",
        "/hair-fusion",
        "/hair/style",
        "/hair"
    ]

    def _make_url_candidates(bases: list[str]) -> list[str]:
        urls: list[str] = []
        for b in bases:
            b = (b or "").rstrip("/")
            if not b:
                continue
            urls.append(b)
            for suf in endpoint_suffixes:
                urls.append(f"{b}{suf}")
        # 중복 제거
        seen = set()
        uniq = []
        for u in urls:
            if u not in seen:
                uniq.append(u)
                seen.add(u)
        return uniq

    url_candidates = _make_url_candidates(candidates)

    headers_list = _candidate_headers()
    payload_list = _candidate_payloads(face_url, hair_style, color, image_size, task_type)

    errors: list[str] = []
    async with httpx.AsyncClient() as client:
        for url in url_candidates:
            for headers in headers_list:
                for mode, payload in payload_list:
                    try:
                        return await _try_once(client, url, headers, mode, payload)
                    except AILabAuthError:
                        errors.append(f"{url} -> 401 Unauthorized (headers={list(headers.keys())})")
                        break
                    except AILabBadReq as e:
                        errors.append(f"{url} -> 400 Bad Request (mode={mode}): {str(e)[:120]}")
                        continue
                    except AILabError as e:
                        errors.append(f"{url} -> {str(e)[:160]}")
                        continue
                    except Exception as e:
                        errors.append(f"{url} -> Unexpected: {repr(e)[:160]}")
                        continue

    raise AILabError("All candidates failed.\n" + "\n".join(errors))
