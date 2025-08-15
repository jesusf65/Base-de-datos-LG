import json
import re
from app.utils.logger import setup_logger

logger = setup_logger("message_parser")

SOURCE_ID_PATTERNS = [
    r"sourceId\s*:\s*\"([^\"]+)\"",
    r"sourceId\s*:\s*'([^']+)'",
    r"sourceId\s*:\s*(\d+)",
    r"sourceId\s*:\s*([a-zA-Z0-9_-]+)",
    r"sourceId\s*:\s*([^\s\n,]+)",
    r"source_id\s*:\s*\"([^\"]+)\"",
    r"source_id\s*:\s*'([^']+)'",
    r"source_id\s*:\s*(\d+)",
    r"source_id\s*:\s*([a-zA-Z0-9_-]+)",
    r"source_id\s*:\s*([^\s\n,]+)"
]

def extract_messages_from_response(messages_data):
    """Extrae la lista de mensajes sin importar la estructura."""
    if isinstance(messages_data, dict):
        if "messages" in messages_data:
            if isinstance(messages_data["messages"], dict) and "messages" in messages_data["messages"]:
                return messages_data["messages"]["messages"]
            elif isinstance(messages_data["messages"], list):
                return messages_data["messages"]
        elif "data" in messages_data:
            return messages_data["data"]
        elif "conversations" in messages_data:
            return messages_data["conversations"]
        else:
            for key in messages_data:
                if "message" in key.lower():
                    return messages_data[key]
            return [messages_data]
    elif isinstance(messages_data, list):
        return messages_data
    return []

def classify_messages(messages_list):
    """Clasifica mensajes en inbound y outbound."""
    inbound, outbound, all_msgs = [], [], []
    for msg in reversed(messages_list):
        if isinstance(msg, dict):
            all_msgs.append(msg)
            if msg.get("direction") == "inbound":
                inbound.append(msg)
            elif msg.get("direction") == "outbound":
                outbound.append(msg)
    return inbound, outbound, all_msgs

def find_source_id(messages):
    """Busca el primer sourceId válido en una lista de mensajes."""
    for msg in messages:
        body = msg.get("body", "")
        for pattern in SOURCE_ID_PATTERNS:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return None
