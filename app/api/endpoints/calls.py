from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
import datetime
from email.message import EmailMessage
import aiosmtplib

app = FastAPI()


class LeadData(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    monthly_income: str
    dob: str  # Format: YYYY-MM-DD
    job_start_date: str  # Format: YYYY-MM-DD
    address: str
    move_in_date: str  # Format: YYYY-MM-DD
    buying_timeframe: str = "Next 30 days"  # Optional, default


def build_adf_xml(lead: LeadData) -> str:
    now = datetime.datetime.utcnow().isoformat()

    adf_template = f"""<?xml version="1.0" encoding="utf-8"?>
<adf>
  <prospect>
    <requestdate>{now}</requestdate>
    <customer>
      <contact>
        <name part="first" type="individual">{lead.first_name}</name>
        <name part="last" type="individual">{lead.last_name}</name>
        <email>{lead.email}</email>
        <phone type="voice">{lead.phone}</phone>
      </contact>
    </customer>
    <comment>I am shopping for a vehicle and submitted a prequalification on Westlake Financial. Here are my details:
Monthly Income: ${lead.monthly_income}, DOB: {lead.dob}, Job Start Date: {lead.job_start_date}, Address: {lead.address}, Move-in Date: {lead.move_in_date}, Buying Timeframe: {lead.buying_timeframe}</comment>
    <provider>
      <name>CarZing</name>
    </provider>
  </prospect>
</adf>"""
    return adf_template


async def send_email(xml_content: str):
    msg = EmailMessage()
    msg["Subject"] = "Lead Submission"
    msg["From"] = "tucorreo@gmail.com"
    msg["To"] = "eleads-super-autos-miami-19355@app.autoraptor.com"
    msg.set_content(xml_content)

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=465,
        username="tucorreo@gmail.com",
        password="TU_APP_PASSWORD",  # Usa una App Password de Gmail
        use_tls=True,
    )


@app.post("/webhook/lead")
async def receive_webhook(lead: LeadData):
    xml = build_adf_xml(lead)
    await send_email(xml)
    return {"message": "Lead enviado correctamente"}