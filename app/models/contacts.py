from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.models.base import Base

class ContactoDriverUS(Base):
    __tablename__ = "contactos_driver_us"

    contact_id = Column(String, primary_key=True, index=True)
    contact_name = Column(String, nullable=True)
    create_date = Column(DateTime, nullable=True)
    asign_to = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    source = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    call_count = Column(Integer, default=0)
    custom_fields = Column(JSON, nullable=True) 