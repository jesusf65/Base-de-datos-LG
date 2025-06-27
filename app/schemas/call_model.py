from datetime import datetime
from typing import Optional
from pydantic import UUID4, BaseModel

# Shared properties
class CallModelBase(BaseModel):
    call_id: str = None
    first_name: str= None
    last_name: str = None
    phone_number: str = None
    #id de la llaamada
    #nombre del propietario 
    #duracion de la llamada 
    #link de grabacion de la llamada
    #resultado de la llamada

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
