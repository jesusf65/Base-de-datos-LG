from fastapi import APIRouter, Request
import json
import logging

# Configura el logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("webhook_logger")

router = APIRouter()

@router.post("/webhook")
async def receive_webhook(request: Request):    
    try:
        # Read the request body
        body = await request.body()
        data = json.loads(body)

        # Log the received data
        logger.info(f"Received webhook data: {data}")

        return {"status": "success", "message": "Webhook received successfully"}

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return {"status": "error", "message": "Invalid JSON format"}, 400
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}, 500