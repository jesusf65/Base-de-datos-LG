from uuid import uuid4
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.BaseModel import BaseModel

class CallCrm(BaseModel):
    __tablename__ = 'call_crm'

    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4)
    
    user_from = Column(String(100), nullable=False)
    stamp_time = Column(String(100), nullable=True)
    status_call = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=False)  
    contact_id = Column(String(100), nullable=False)
    direction = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True, default=None)
    