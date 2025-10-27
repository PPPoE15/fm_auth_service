from fastapi import APIRouter

from apps.web.app.handlers.api.user.endpoints import router as user_router

main_router = APIRouter()


main_router.include_router(user_router)
