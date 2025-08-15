from fastapi import APIRouter, Request, HTTPException
from app.services import leadconnector, message_parser, webhook_sender
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("webhook_router")

@router.post("/webhook")
async def receive_webhook(request: Request):
    try:
        data = await request.json()
        contact_id = data.get("contact_id")
        if not contact_id:
            raise HTTPException(status_code=400, detail="El campo contact_id es requerido")

        conversations = leadconnector.get_conversations_by_contact(contact_id)
        if not conversations or not conversations.get("conversations"):
            return {"status": "success", "message": "No se encontraron conversaciones"}

        all_source_ids = set()
        enriched_conversations = []

        for conv in conversations["conversations"]:
            conv_id = conv["id"]
            messages_data = leadconnector.get_conversation_messages(conv_id)
            messages_list = message_parser.extract_messages_from_response(messages_data)
            inbound, outbound, all_msgs = message_parser.classify_messages(messages_list)

            source_id = message_parser.find_source_id(inbound) or message_parser.find_source_id(outbound)
            if source_id:
                all_source_ids.add(source_id)

            enriched_conversations.append({
                "conversation_id": conv_id,
                "last_message": conv.get("lastMessageBody"),
                "source_id": source_id,
                "total_messages": len(all_msgs)
            })

        if all_source_ids:
            webhook_sender.send_source_id_to_webhook(list(all_source_ids)[0], contact_id)

        return {
            "status": "success",
            "contact_id": contact_id,
            "source_id": source_id,
            "source_ids_contact": list(all_source_ids),
            "conversations": enriched_conversations
        }

    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
