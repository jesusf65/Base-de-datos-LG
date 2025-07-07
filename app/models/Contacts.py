from uuid import uuid4
from sqlalchemy import Column, DateTime, String, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship     

from app.models.BaseModel import BaseModel

class Contact(BaseModel):
    __tablename__ = 'contact'

    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4)
    
    contact_id = Column(String(50), nullable=False)
    contact_name = Column(String(50), nullable=False)
    create_date = Column(String(50), nullable=False)
    asign_to = Column(String(50), nullable=False)  
    phone_number = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    tags = Column(Text, nullable=False)
    call_count = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True, default=None)
    
calls = relationship("CallModel", back_populates="contact")