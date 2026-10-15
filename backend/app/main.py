from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.game import router as game_router
from app.api.profile import router as profile_router

app = FastAPI(title="No Riichi No Fuku API")
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(game_router)
app.include_router(profile_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
