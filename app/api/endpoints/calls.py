from fastapi import APIRouter, Request
import json
from logging import getLogger

router = APIRouter()

@router.post("/webhook")
async def receive_webhook(request: Request):
    logger = getLogger("webhook_logger")
    
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