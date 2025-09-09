from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class ContactModel(BaseModel):
    contact_id: str
    contact_name: Optional[str] = None
    create_date: Optional[datetime] = None
    asign_to: Optional[str] = None
    phone_number: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[str] = None
    call_count: Optional[int] = 0
    custom_fields: Optional[List[Dict[str, Any]]] = None

# Properties to receive via API on creation
class CallModelCreate(ContactModel):
    pass

class CallModelUpdate(ContactModel):
    pass

# Properties stored in DB
class CallModelInDb(ContactModel):
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class CallModelSesion(ContactModel):
    pass
