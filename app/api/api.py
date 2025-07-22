from fastapi import APIRouter

from app.api.endpoints.calls import router as router_calls
from app.api.endpoints.health_check import router as router_check    
from app.api.endpoints.debug import router as router_debug

api_router = APIRouter()

api_router.include_router(router_calls, tags=["GHL webhook"],
    responses={404: {"description": "Not found"}})

#route Checkout
api_router.include_router(router_check, tags=["HealthCheck"],
    responses={404: {"description": "Not found"}})

api_router.include_router(router_debug, tags=["Debug"],
    responses={404: {"description": "Not found"}})