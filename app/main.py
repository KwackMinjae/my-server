from __future__ import annotations
# hairfusion-service/app/main.py

from typing import Optional, Dict, Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.settings import settings

# ---- AILabTools (2D 헤어 합성) ----
from app.services.ailabtools import (
    hairstyle_edit_pro,
    AILabError,
    AILabAuthError,
    AILabBadReq,
)

# ---- Meshy (2D → 3D 변환) ----
# ⚠ meshy.py 에 정의된 실제 함수 이름에 맞춰 임포트
from app.services.meshy import (
    create_image_to_3d,
    wait_and_download,
    get_job,
    MeshyError,
    MeshyAuthError,
    MeshyBadReq,
    MeshyTimeout,
)

import httpx  # AsyncClient 사용

# -------------------------------------
# FastAPI 초기화
# -------------------------------------
app = FastAPI(title="HairFusion Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "allowed_origins", ["*"])),

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
from app.routes import uploads

app = FastAPI(title="Hair3D API")

origins = settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 정적 파일 서빙 (outputs/*)
app.mount("/static", StaticFiles(directory="outputs"), name="static")


# -------------------------------------
# Pydantic Schemas
# -------------------------------------
class FuseReq(BaseModel):
    face_url: str
    hair_style: Optional[str] = None
    color: Optional[str] = None
    image_size: Optional[int] = None
    task_type: Optional[str] = "sync"


class MeshifyReq(BaseModel):
    image_url: str


# -------------------------------------
# Health Check
# -------------------------------------
@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok\n--\nTrue\n"


# -------------------------------------
# AILabTools: 2D 헤어 합성
# -------------------------------------
@app.post("/fuse")
async def fuse(req: FuseReq) -> Dict[str, Any]:
    """
    AILabTools를 이용해 2D 헤어스타일 합성 수행.
    합성 결과 이미지를 outputs/ 폴더에 저장하고 파일 경로 반환.
    """
    try:
        saved = await hairstyle_edit_pro(
            face_url=req.face_url,
            hair_style=req.hair_style,
            color=req.color,
            image_size=req.image_size,
            task_type=req.task_type,
        )
        return {"saved_path": saved, "ok": True}
    except AILabAuthError as e:
        raise HTTPException(status_code=401, detail=f"auth error: {str(e)[:400]}")
    except AILabBadReq as e:
        raise HTTPException(status_code=400, detail=f"bad request: {str(e)[:400]}")
    except AILabError as e:
        raise HTTPException(status_code=502, detail=f"backend error: {str(e)[:400]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unexpected: {repr(e)[:400]}")


# -------------------------------------
# Meshy: 2D → 3D 변환
# -------------------------------------
@app.post("/meshify")
async def meshify(req: MeshifyReq) -> Dict[str, Any]:
    """
    Meshy(OpenAPI v1)를 이용해 이미지→3D 변환을 수행하고,
    결과 GLB를 저장한 뒤 경로와 작업 상세를 반환한다.
    """
    try:
        # 1) 작업 생성 (task_id 반환)
        task_id = await create_image_to_3d(req.image_url)

        # 2) 완료까지 대기하며 모델(GLB) 다운로드 -> 로컬 경로 반환
        saved_path = await wait_and_download(task_id)

        # 3) 최종 작업 상세 조회
        task_json = await get_job(task_id)

        return {"job_id": task_id, "saved_path": str(saved_path), "result": task_json}

    except MeshyAuthError as e:
        raise HTTPException(status_code=401, detail=f"meshy auth: {str(e)[:400]}")
    except MeshyBadReq as e:
        raise HTTPException(status_code=400, detail=f"meshy bad request: {str(e)[:400]}")
    except MeshyTimeout as e:
        raise HTTPException(status_code=504, detail=f"meshy timeout: {str(e)[:400]}")
    except MeshyError as e:
        raise HTTPException(status_code=502, detail=f"meshy error: {str(e)[:400]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unexpected: {repr(e)[:400]}")


# -------------------------------------
# 간단한 3D 뷰어 (model-viewer)
# -------------------------------------
@app.get("/viewer", response_class=HTMLResponse)
def viewer(file: str) -> str:
    """
    outputs/meshy/<file> 을 model-viewer로 브라우저에서 미리보기.
    예시: http://127.0.0.1:8100/viewer?file=meshy_xxx.glb
    """
    safe = quote(file)
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>HairFusion 3D Viewer</title>
    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    <style>
      html, body {{ height:100%; margin:0; background:#111; color:#eee; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
      header {{ padding:10px 16px; background:#181818; border-bottom:1px solid #222; }}
      main {{ height: calc(100% - 52px); }}
      model-viewer {{ width:100%; height:100%; }}
      a {{ color:#9ad; text-decoration:none; }}
      a:hover {{ text-decoration:underline; }}
    </style>
  </head>
  <body>
    <header>
      <strong>HairFusion 3D Viewer</strong>
      &nbsp;·&nbsp;
      <a href="/static/meshy/{safe}" target="_blank">Download GLB</a>
    </header>
    <main>
      <model-viewer
        src="/static/meshy/{safe}"
        ar
        camera-controls
        autoplay
        environment-image="neutral"
        shadow-intensity="0.8"
        exposure="1.0"
      ></model-viewer>
    </main>
  </body>
</html>
    """


# -------------------------------------
# 전역 예외 핸들러 (안심용)
# -------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        {"detail": f"UNHANDLED: {repr(exc)}"},
        status_code=500,
    )


# -------------------------------------
# 로컬 실행 진입점 (선택)
# -------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8100, reload=True)



@app.get("/health")
def health():
    return {"ok": True}