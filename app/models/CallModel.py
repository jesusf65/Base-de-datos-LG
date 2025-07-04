from uuid import uuid4
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.BaseModel import BaseModel

class CallModel(BaseModel):
    __tablename__ = 'calls'

    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4)
    
    call_id = Column(String(50), nullable=False)
    time_stamp = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False)  
    direct_link = Column(String(50), nullable=False)
    id_user = Column(String(50), nullable=False)
    phone_number = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True, default=None)
    
contact = relationship("Contact", backpopulates="contacts_table", uselist=False)