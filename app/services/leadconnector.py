import http.client
import json
from app.utils.logger import setup_logger

logger = setup_logger("leadconnector_service")

LEADCONNECTOR_API_KEY = "Bearer pit-6cd3fee8-5d37-47e4-b2ea-0cc628ceb84f"
LEADCONNECTOR_HOST = "services.leadconnectorhq.com"
LEADCONNECTOR_VERSION = "2021-04-15"

def _make_request(method: str, endpoint: str):
    conn = http.client.HTTPSConnection(LEADCONNECTOR_HOST)
    headers = {
        "Accept": "application/json",
        "Version": LEADCONNECTOR_VERSION,
        "Authorization": LEADCONNECTOR_API_KEY
    }
    conn.request(method, endpoint, headers=headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    if response.status >= 400:
        logger.error(f"❌ Error {response.status} - {data}")
        return None
    return json.loads(data)

def get_conversations_by_contact(contact_id: str):
    endpoint = f"/conversations/search?contactId={contact_id}"
    return _make_request("GET", endpoint)

def get_conversation_messages(conversation_id: str, limit: int = 10):
    endpoint = f"/conversations/{conversation_id}/messages?limit={limit}"
    return _make_request("GET", endpoint)
