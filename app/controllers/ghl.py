import httpx
import os
import dotenv
from app.core.settings import get_settings
import logging

dotenv.load_dotenv()
logger = logging.getLogger(__name__)
API_KEY_CRM = get_settings().API_KEY_CRM

dotenv.load_dotenv()
CUSTOM_FIELD_KEY = "veces_contactado"
CUSTOM_FIELD_ID = "MUiuwmOLvjHwYBmktZt7" 
"""
    Controlador para interactuar con la API de GoHighLevel.
    """
class GhlController:
    """
    Controlador para interactuar con la API de GoHighLevel.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://rest.gohighlevel.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    async def get_contact_by_phone(self, phone_number: str):
        """Busca un contacto en GoHighLevel por su número de teléfono."""
        url = f"{self.base_url}/contacts/lookup"
        normalized_phone = "".join(filter(str.isdigit, phone_number))
        params = {"phone": f"+{normalized_phone}"} 
        
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Buscando contacto en GHL con teléfono: {normalized_phone}")
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("contacts") and len(data["contacts"]) > 0:
                    contact = data["contacts"][0]
                    logger.info(f"Contacto encontrado: ID {contact.get('id')}")
                    return contact
                else:
                    logger.warning(f"No se encontró ningún contacto con el teléfono: {normalized_phone}")
                    return None
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP al buscar contacto en GHL: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error inesperado al buscar contacto: {e}")
                return None

    async def update_contact_call_count(self, contact_id: str):
        """
        Versión definitiva: Actualiza el campo 'veces_contactado' de forma incremental,
        usando el ID para la creación y la KEY para la actualización.
        """
        update_url = f"{self.base_url}/contacts/{contact_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Obtener los datos actuales del contacto
                get_response = await client.get(update_url, headers=self.headers)
                get_response.raise_for_status()
                contact_data = get_response.json().get("contact", {})
                
                custom_fields = contact_data.get("customFields", [])
                if custom_fields is None:
                    custom_fields = []

                call_count = 0
                field_found = False

                # 2. Buscar el campo por su 'key' o 'id' para actualizarlo
                for field in custom_fields:
                    if field.get("key") == CUSTOM_FIELD_KEY or field.get("id") == CUSTOM_FIELD_ID:
                        try:
                            current_value = field.get("value", "0")
                            call_count = int(float(current_value)) if current_value else 0
                        except (ValueError, TypeError):
                            call_count = 0
                        
                        field['value'] = call_count + 1
                        field_found = True
                        break
                
                # 3. Si el campo no existía, lo añadimos usando su ID y Key
                if not field_found:
                    custom_fields.append({
                        "id": CUSTOM_FIELD_ID,
                        "key": CUSTOM_FIELD_KEY,
                        "value": 1
                    })

                # 4. Preparar el payload con la lista completa de campos
                update_payload = {
                    "customFields": custom_fields
                }
                
                new_value = next((f['value'] for f in custom_fields if f.get('key') == CUSTOM_FIELD_KEY), 'N/A')
                logger.info(f"Actualizando contacto ID {contact_id}. Nuevo contador para '{CUSTOM_FIELD_KEY}': {new_value}")
                
                # 5. Enviar la petición PUT para actualizar
                put_response = await client.put(update_url, headers=self.headers, json=update_payload)
                put_response.raise_for_status()
                
                logger.info(f"Contacto ID {contact_id} actualizado correctamente.")
                return put_response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP al actualizar contacto {contact_id}: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error inesperado al actualizar contacto {contact_id}: {e}")
                return None

# Instanciamos el controlador
ghl_controller = GhlController(api_key=API_KEY_CRM)
