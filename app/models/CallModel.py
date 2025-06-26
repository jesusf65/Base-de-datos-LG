from uuid import uuid4
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.BaseModel import BaseModel

class CallModel(BaseModel):
    __tablename__ = 'calls'

    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4)
    
    call_id = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)  
    phone_number = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True, default=None)
    