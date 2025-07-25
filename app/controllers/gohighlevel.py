                                                                                          
import httpx
import os
import dotenv
from app.core.settings import get_settings

dotenv.load_dotenv()

API_KEY_CRM = get_settings().API_KEY_CRM
GHL_BASE_URL = "https://api.msgsndr.com/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY_CRM}",
    "Content-Type": "application/json"
}

async def obtener_contacto(contact_id: str):
    url = f"{GHL_BASE_URL}/contacts/{contact_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        return None
