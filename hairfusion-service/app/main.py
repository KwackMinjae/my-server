from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional

from app.services.ailabtools import (
    hairstyle_edit_pro, AILabError, AILabAuthError, AILabBadReq
)
from app.settings import settings

app = FastAPI(title="HairFusion Service")

class FuseReq(BaseModel):
    face_url: HttpUrl
    hair_style: Optional[str] = None
    color: Optional[str] = None
    image_size: Optional[int] = None   # 1~4
    task_type: Optional[str] = "async" # 가능하면 async/sync

@app.post("/fuse")
async def fuse(req: FuseReq):
    try:
        path = await hairstyle_edit_pro(
            face_url=str(req.face_url),
            hair_style=req.hair_style,
            color=req.color,
            image_size=req.image_size,
            task_type=req.task_type,
        )
        return {"status": "ok", "result_path": path}
    except AILabAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except AILabBadReq as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AILabError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected: {e}")

@app.get("/health")
def health():
    return {"ok": True, "urls": settings.ailab_base_urls}
