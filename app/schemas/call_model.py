from datetime import datetime
from typing import Optional
from pydantic import UUID4, BaseModel

# Shared properties
class CallModelBase(BaseModel):
    call_id: str = None
    time_stamp: str= None
    direction: str = None
    direct_link: str = None
    id_user: str = None
    phone_number: str = None
    status: str = None

# Properties to receive via API on creation
class CallModelCreate(CallModelBase):
    pass

class CallModelUpdate(CallModelBase):
    pass
class CallModelInDb(CallModelBase):
    uuid: UUID4
    created_at: datetime = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class CallModelSesion(CallModelBase):
    pass
