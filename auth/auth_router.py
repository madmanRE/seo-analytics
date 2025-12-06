from fastapi import APIRouter

from auth.gsc_auth.gsc_router import gsc_router
from auth.yandex_auth.yandex_router import yandex_router

auth_router = APIRouter(prefix="/auth")
auth_router.include_router(gsc_router)
auth_router.include_router(yandex_router)