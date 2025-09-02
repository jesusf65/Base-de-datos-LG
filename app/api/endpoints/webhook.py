from fastapi import APIRouter

from app.controllers.ghl import ghl_controller  

router = APIRouter()

@router.get("/ghl-contacts")
async def ghl_contacts():
    ghl_contacts = await ghl_controller.get_ghl_contacts()
    return ghl_contacts  