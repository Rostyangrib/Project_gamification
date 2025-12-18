from fastapi import APIRouter

router = APIRouter()

from routes_post import router as post_router
from routes_get import router as get_router
from routes_put import router as put_router
from routes_delete import router as delete_router
from routes_chat import router as chat_router

router.include_router(post_router)
router.include_router(get_router)
router.include_router(put_router)
router.include_router(delete_router)

router.include_router(chat_router)