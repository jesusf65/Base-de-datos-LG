from fastapi import APIRouter

from app.api.endpoints.calls import router as router_calls
from app.api.endpoints.ghl_contacts import router as router_ghl__contacts
from app.api.endpoints.health_check import router as router_check    

api_router = APIRouter()

api_router.include_router(router_calls, tags=["GHL webhook"],
    responses={404: {"description": "Not found"}})

api_router.include_router(router_ghl__contacts, tags=["Ghl Contacts"],
    responses={404: {"description": "Not found"}})

#route Checkout
api_router.include_router(router_check, tags=["HealthCheck"],
    responses={404: {"description": "Not found"}})
    
