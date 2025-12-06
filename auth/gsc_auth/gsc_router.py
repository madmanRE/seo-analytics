from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from auth.gsc_auth.gsc import create_flow

gsc_router = APIRouter(prefix="/google", tags=["Google Auth"])

@gsc_router.get("/login", description="127.0.0.1:8000/auth/google/login")
async def google_login():
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return RedirectResponse(auth_url)


@gsc_router.get("/callback")
async def google_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return JSONResponse({"error": "Missing authorization code"}, status_code=400)

    flow = create_flow()
    flow.fetch_token(code=code)

    creds = flow.credentials

    request.session["google_token"] = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    return RedirectResponse(url="/")