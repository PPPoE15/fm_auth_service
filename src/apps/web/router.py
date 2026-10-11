from fastapi import APIRouter

from apps.modules.session.api import router as session_router
from apps.modules.user.api import router as user_router

main_router = APIRouter()


main_router.include_router(user_router)
main_router.include_router(session_router)
