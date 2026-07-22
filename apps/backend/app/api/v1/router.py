from fastapi import APIRouter, Depends
from app.api.v1.auth import router as auth_router
from app.core.deps import verify_csrf

api_router = APIRouter(dependencies=[Depends(verify_csrf)])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
