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
        """
        Paso 1: Busca un contacto en GoHighLevel por su número de teléfono.
        Devuelve el primer contacto que coincida.
        """
        url = f"{self.base_url}/contacts/lookup"
        # Normalizamos el número de teléfono eliminando caracteres no numéricos
        normalized_phone = "".join(filter(str.isdigit, phone_number))
        
        # La API de GHL a menudo espera el formato E.164, pero puede funcionar sin el '+'
        # Probamos con el formato más común primero.
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
                logger.error(f"Error al buscar contacto en GHL: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error inesperado al buscar contacto: {e}")
                return None

    async def update_contact_call_count(self, contact_id: str):
        """
        Actualiza el campo personalizado 'veces_contactado' de forma incremental,
        preservando otros campos personalizados.
        """
        update_url = f"{self.base_url}/contacts/{contact_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Obtener los datos actuales del contacto para leer la lista completa de campos
                get_response = await client.get(update_url, headers=self.headers)
                get_response.raise_for_status()
                contact_data = get_response.json().get("contact", {})
                
                # Obtenemos una copia de la lista de campos personalizados existentes
                custom_fields = contact_data.get("customFields", [])
                if custom_fields is None:
                    custom_fields = []

                call_count = 0
                field_found = False

                # 2. Buscamos el campo por su 'key' para actualizarlo DENTRO de la lista
                for field in custom_fields:
                    if field.get("key") == CUSTOM_FIELD_KEY:
                        try:
                            # Obtenemos el valor actual y lo convertimos a número
                            current_value = field.get("value", "0")
                            call_count = int(float(current_value)) if current_value else 0
                        except (ValueError, TypeError):
                            call_count = 0 # Si no es un número, reseteamos a 0
                        
                        # Incrementamos y actualizamos el valor en la lista existente
                        field['value'] = call_count + 1
                        field_found = True
                        break
                
                # 3. Si el campo no existía en la lista del contacto, lo añadimos
                if not field_found:
                    custom_fields.append({
                        "key": CUSTOM_FIELD_KEY,
                        "value": 1
                    })

                # 4. Preparamos el payload para la actualización CON LA LISTA COMPLETA
                # Esto evita que se borren otros campos personalizados del contacto.
                update_payload = {
                    "customFields": custom_fields
                }
                
                new_value = next((f['value'] for f in custom_fields if f['key'] == CUSTOM_FIELD_KEY), 'N/A')
                logger.info(f"Actualizando contacto ID {contact_id}. Payload completo enviado. Nuevo contador para '{CUSTOM_FIELD_KEY}': {new_value}")
                
                # 5. Enviamos la petición PUT con la lista de campos actualizada
                put_response = await client.put(update_url, headers=self.headers, json=update_payload)
                put_response.raise_for_status()
                
                logger.info(f"Contacto ID {contact_id} actualizado correctamente.")
                return put_response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Error al actualizar contacto {contact_id}: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error inesperado al actualizar contacto {contact_id}: {e}")
                return None


# Instanciamos el controlador una sola vez
ghl_controller = GhlController(api_key=API_KEY_CRM)
