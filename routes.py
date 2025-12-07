from fastapi import APIRouter

router = APIRouter()

from routes_post import router as post_router
from routes_get import router as get_router
from routes_put import router as put_router

router.include_router(post_router)
router.include_router(get_router)
router.include_router(put_router)