import hashlib
import hmac
import json
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from config import BOT_TOKEN, MINI_APP_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Mini App API", version="1.0.0")

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статику (HTML/JS/CSS для Mini App)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    return {"status": "ok", "service": "mini-app-api"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------- Валидация Telegram WebApp initData ----------


def validate_init_data(init_data: str, bot_token: str) -> bool:
    """
    Проверяет подпись initData от Telegram WebApp.
    """
    try:
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[urllib.parse.unquote(key)] = urllib.parse.unquote(value)

        received_hash = params.get("hash", "")
        if not received_hash:
            return False

        data_check_params = {k: v for k, v in params.items() if k != "hash"}
        sorted_items = sorted(data_check_params.items(), key=lambda x: x[0])
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

        secret_key = hmac.new(
            bot_token.encode(), "WebAppData".encode(), hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception as e:
        logger.error(f"initData validation error: {e}")
        return False


def parse_init_data_user(init_data: str) -> Optional[dict]:
    """Извлекает объект пользователя из initData (поле 'user' — JSON)."""
    try:
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[urllib.parse.unquote(key)] = urllib.parse.unquote(value)

        user_json = params.get("user")
        if not user_json:
            return None
        return json.loads(user_json)
    except Exception as e:
        logger.error(f"parse init_data user error: {e}")
        return None


# ---------- Модели ----------


class ProfileSaveRequest(BaseModel):
    init_data: str
    display_name: Optional[str] = None
    is_anonymous: bool = False


# ---------- Эндпоинты ----------


@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = Query(10, ge=1, le=50)):
    """Возвращает топ пользователей по количеству предложений."""
    top = await db.get_top_users(limit=limit)
    return {"users": top}


@app.post("/api/profile/save")
async def save_profile(request: ProfileSaveRequest):
    """Сохраняет выбор пользователя (никнейм / анонимность)."""
    if not validate_init_data(request.init_data, BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid initData")

    user = parse_init_data_user(request.init_data)
    if not user:
        raise HTTPException(status_code=400, detail="Cannot extract user from initData")

    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in initData")

    await db.save_user_profile(
        user_id=user_id,
        display_name=request.display_name,
        is_anonymous=request.is_anonymous,
    )

    return {"status": "saved", "user_id": user_id}


@app.get("/api/profile/me")
async def get_my_profile(init_data: str = Query(...)):
    """Возвращает профиль текущего пользователя из initData."""
    if not validate_init_data(init_data, BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid initData")

    user = parse_init_data_user(init_data)
    if not user:
        raise HTTPException(status_code=400, detail="Cannot extract user from initData")

    user_id = user.get("id")
    profile = await db.get_user_profile(user_id)
    if not profile:
        return {"user_id": user_id, "display_name": None, "is_anonymous": False, "exists": False}

    return {"user_id": user_id, "exists": True, **profile}


@app.get("/miniapp")
async def miniapp_index():
    """Отдаёт HTML-файл Mini App."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))