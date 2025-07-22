from datetime import datetime
from typing import Optional
from pydantic import UUID4, BaseModel

# Shared properties
class ContactModel(BaseModel):
    contact_id: str = None
    contact_name: str = None
    create_date: str = None
    asing_to: str = None
    phone_number: str = None
    source: str = None
    tags: str = None
    call_count:  str = None

# Properties to receive via API on creation
class CallModelCreate(ContactModel):
    pass

class CallModelUpdate(ContactModel):
    pass
class CallModelInDb(ContactModel):
    uuid: UUID4
    created_at: datetime = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class CallModelSesion(ContactModel):
    pass