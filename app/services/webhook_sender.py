import http.client
import json
from app.utils.logger import setup_logger
from app.services.leadconnector import LEADCONNECTOR_API_KEY, LEADCONNECTOR_VERSION

logger = setup_logger("webhook_sender")

def send_source_id_to_webhook(source_id, contact_id):
    target_host = "services.leadconnectorhq.com"
    target_endpoint = "/hooks/fwnI1qTmRiENU4TmxNZ4/webhook-trigger/a4b083f2-4a71-4cab-8c00-e8c47bf85f17"
    
    conn = http.client.HTTPSConnection(target_host)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": LEADCONNECTOR_VERSION,
        "Authorization": LEADCONNECTOR_API_KEY
    }
    payload = json.dumps({
        "sourceId": source_id,
        "contactId": contact_id
    })
    conn.request("POST", target_endpoint, body=payload, headers=headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    if response.status >= 400:
        logger.error(f"❌ Error enviando al webhook: {response.status} - {data}")
    else:
        logger.info(f"✅ Webhook enviado: {data}")
