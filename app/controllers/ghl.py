import httpx
import os
import dotenv
from app.core.settings import get_settings

dotenv.load_dotenv()

API_KEY_CRM = get_settings().API_KEY_CRM


class GhlController:
    async def get_ghl_contacts(self):
        url = "https://rest.gohighlevel.com/v1/contacts/"
        headers = {
            "Authorization": f"Bearer {API_KEY_CRM}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Lanza una excepción si hay error
            return response.json()

ghl_controller = GhlController()    