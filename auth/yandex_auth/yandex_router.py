import os

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

load_dotenv()

yandex_router = APIRouter(prefix="/yandex", tags=["Yandex Auth"])

YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/auth/yandex/callback"


@yandex_router.get("/login", description="127.0.0.1:8000/auth/yandex/login")
async def yandex_login():
    auth_url = (
        f"https://oauth.yandex.com/authorize?"
        f"response_type=code&client_id={YANDEX_CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)


@yandex_router.get("/callback")
async def yandex_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "Missing authorization code"}, status_code=400)

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": YANDEX_CLIENT_ID,
        "client_secret": YANDEX_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth.yandex.com/token", data=data)
        token_data = resp.json()

    request.session["yandex_token"] = token_data

    return RedirectResponse(url="/")
