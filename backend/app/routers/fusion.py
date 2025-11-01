from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.services.hairfusion_client import fuse_hair, HairFusionError

router = APIRouter(prefix="/fusion", tags=["hair-fusion"])

class FusionReq(BaseModel):
    face_url: HttpUrl
    hair_style: Optional[str] = None
    color: Optional[str] = None
    image_size: Optional[int] = None   # 1~4
    task_type: Optional[str] = "async" # 기본 async

@router.post("/hair")
async def fusion_hair(req: FusionReq):
    try:
        resp = await fuse_hair(
            face_url=str(req.face_url),
            hair_style=req.hair_style,
            color=req.color,
            image_size=req.image_size,
            task_type=req.task_type or "async",
        )
        return resp
    except HairFusionError as e:
        # hairfusion-service에서 온 에러를 502로 래핑
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected: {e}")
