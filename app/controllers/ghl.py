import httpx
import asyncio
from typing import List, Dict, Any
import dotenv
from app.core.settings import get_settings

dotenv.load_dotenv()

API_KEY_CRM = get_settings().API_KEY_CRM


class GhlController:
    async def get_all_ghl_contacts(self) -> Dict[str, Any]:
        """
        Obtiene todos los contactos de GHL mediante paginación automática
        Returns:
            Dict con información de los contactos y conteo total
        """
        all_contacts = []
        page = 1
        limit = 100  # Puedes ajustar este valor (máximo permitido por la API)
        total_contacts = 0
        
        while True:
            try:
                url = f"https://rest.gohighlevel.com/v1/contacts/?page={page}&limit={limit}"
                headers = {
                    "Authorization": f"Bearer {API_KEY_CRM}"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extraer contactos de la página actual
                    contacts = data.get('contacts', [])
                    all_contacts.extend(contacts)
                    
                    # Verificar si hay más páginas
                    if not contacts or len(contacts) < limit:
                        break
                        
                    page += 1
                    
                    # Pequeña pausa para no saturar la API
                    await asyncio.sleep(0.1)
                    
            except httpx.HTTPStatusError as e:
                print(f"Error en página {page}: {e}")
                break
            except Exception as e:
                print(f"Error inesperado: {e}")
                break
        
        total_contacts = len(all_contacts)
        
        return {
            "total_contacts": total_contacts,
            "contacts": all_contacts,
            "pages_processed": page
        }

    async def get_contacts_count_only(self) -> Dict[str, int]:
        """
        Obtiene solo el conteo de contactos sin traer todos los datos
        Returns:
            Dict con el conteo total de contactos
        """
        try:
            # Primera llamada para obtener metadata
            url = "https://rest.gohighlevel.com/v1/contacts/?page=1&limit=1"
            headers = {
                "Authorization": f"Bearer {API_KEY_CRM}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Algunas APIs devuelven metadata con el total
                total_contacts = data.get('meta', {}).get('total', 0)
                
                if total_contacts > 0:
                    return {
                        "total_contacts": total_contacts,
                        "message": f"Total de contactos: {total_contacts}"
                    }
                else:
                    # Si no hay metadata, contamos manualmente
                    all_data = await self.get_all_ghl_contacts()
                    return {
                        "total_contacts": all_data["total_contacts"],
                        "message": f"Total de contactos: {all_data['total_contacts']}"
                    }
                    
        except Exception as e:
            print(f"Error obteniendo conteo: {e}")
            return {"total_contacts": 0, "message": "Error al obtener conteo"}

    # Métodos originales (para compatibilidad)
    async def get_ghl_contacts(self):
        """Método original - obtiene primera página"""
        return await self.pagination_ghl_contacts(1, 50)

    async def pagination_ghl_contacts(self, page: int = 1, limit: int = 50):
        """Método original - paginación específica"""
        url = f"https://rest.gohighlevel.com/v1/contacts/?page={page}&limit={limit}"
        headers = {
            "Authorization": f"Bearer {API_KEY_CRM}"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()


# Instancia del controlador
ghl_controller = GhlController()