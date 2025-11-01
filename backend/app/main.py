from fastapi import FastAPI
from app.routers import fusion

app = FastAPI(title="Hair3D API")

app.include_router(fusion.router)

@app.get("/health")
def health():
    return {"ok": True}