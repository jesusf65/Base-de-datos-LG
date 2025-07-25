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

    if response.status_code == 200:
        data = response.json()
        contactos = data.get("contacts", [])
        if contactos:
            return contactos[0]  # Puedes adaptar para devolver todos si prefieres
        return None
    else:
        print(f"Error al buscar contacto: {response.status_code}, {response.text}")
        return None
