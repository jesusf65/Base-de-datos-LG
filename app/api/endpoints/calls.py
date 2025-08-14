from fastapi import APIRouter, Request, HTTPException
import json
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_logger")

@router.post("/webhook")
async def receive_webhook(request: Request):    
        body = await request.body()
        data = json.loads(body)
        logger.info(f"Payload recibido en /webhook: {json.dumps(data, indent=2)}")

