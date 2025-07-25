import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_CRM = os.getenv("GHL_API_KEY")
GHL_BASE_URL = "https://rest.gohighlevel.com/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY_CRM}",
    "Content-Type": "application/json"
}

async def buscar_contacto_por_telefono(telefono: str):
    url = f"{GHL_BASE_URL}/contacts/lookup"
    params = {
        "phone": telefono
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS, params=params)

    print(f"📞 Lookup GHL status: {response.status_code}")
    print(f"🔍 Lookup GHL response: {response.text}")

    if response.status_code != 200:
        return None

    data = response.json()
    contactos = data.get("contacts", [])
    if contactos and isinstance(contactos, list):
        return contactos[0]  # Devuelve el primero
    return None
