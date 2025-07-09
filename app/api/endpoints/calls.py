from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LeadData(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    monthly_income: str
    dob: str  # YYYY-MM-DD
    job_start_date: str
    address: str
    move_in_date: str
    buying_timeframe: str = "Next 30 days"


@router.post("/webhook/lead")
async def receive_webhook(lead: LeadData):
    print("📥 Nuevo lead recibido del CRM:")
    print(f"Nombre: {lead.first_name} {lead.last_name}")
    print(f"Email: {lead.email}")
    print(f"Teléfono: {lead.phone}")
    print(f"Ingreso mensual: {lead.monthly_income}")
    print(f"Fecha de nacimiento: {lead.dob}")
    print(f"Inicio de trabajo: {lead.job_start_date}")
    print(f"Dirección: {lead.address}")
    print(f"Fecha de mudanza: {lead.move_in_date}")
    print(f"Tiempo estimado de compra: {lead.buying_timeframe}")
    return {"status": "ok", "message": "Lead recibido correctamente"}