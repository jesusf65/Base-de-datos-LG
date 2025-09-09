from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.controllers.ghl import ghl_controller
from app.core.database import get_session
from app.controllers.contacto_services import save_contacts
from app.schemas.contacts import CallModelInDb
from typing import List

router = APIRouter()

@router.post("/sync-contacts", response_model=List[CallModelInDb])
async def sync_contacts(db: Session = Depends(get_session)):
    """
    Descarga todos los contactos desde GHL y los guarda en la base de datos
    """
    try:
        result = await ghl_controller.get_all_ghl_contacts()
        contacts = result["contacts"]

        if not contacts:
            return []

        saved = save_contacts(db, contacts)

        return saved

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sincronizando: {str(e)}")
    