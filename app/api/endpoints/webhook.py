from fastapi import APIRouter, HTTPException
from app.controllers.ghl import ghl_controller  

router = APIRouter()

@router.get("/ghl-contacts")
async def ghl_contacts():
    ghl_contacts = await ghl_controller.get_ghl_contacts()
    return ghl_contacts  

@router.get("/contacts-pagination")
async def contacts_pagination(page: int = 1, limit: int = 50):
    contacts = await ghl_controller.pagination_ghl_contacts(page=page, limit=limit)
    return contacts

# Nuevos endpoints para paginación automática y conteo
@router.get("/all-contacts")
async def get_all_contacts():
    """
    Obtiene todos los contactos mediante paginación automática
    Returns:
        Información completa con todos los contactos y conteo total
    """
    try:
        result = await ghl_controller.get_all_ghl_contacts()
        return {
            "success": True,
            "total_contacts": result["total_contacts"],
            "pages_processed": result["pages_processed"],
            "contacts_count": len(result["contacts"]),
            "contacts": result["contacts"]  # Puedes omitir esto si solo quieres el conteo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo contactos: {str(e)}")

@router.get("/contacts-count")
async def get_contacts_count():
    """
    Obtiene solo el número total de contactos
    Returns:
        Conteo total de contactos
    """
    try:
        result = await ghl_controller.get_contacts_count_only()
        return {
            "success": True,
            "total_contacts": result["total_contacts"],
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo conteo: {str(e)}")

@router.get("/contacts-summary")
async def get_contacts_summary():
    """
    Obtiene un resumen de los contactos sin la lista completa
    Returns:
        Resumen con conteo y metadata
    """
    try:
        result = await ghl_controller.get_all_ghl_contacts()
        return {
            "success": True,
            "total_contacts": result["total_contacts"],
            "pages_processed": result["pages_processed"],
            "message": f"Se encontraron {result['total_contacts']} contactos en {result['pages_processed']} páginas"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo resumen: {str(e)}")