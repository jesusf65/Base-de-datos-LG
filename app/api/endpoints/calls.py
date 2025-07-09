from fastapi import APIRouter, Request
import json
import datetime
from email.message import EmailMessage
import aiosmtplib

router = APIRouter()

@router.post("/webhook/lead")
async def receive_webhook(request: Request):
    payload = await request.json()

    print("📥 Webhook recibido:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Extraer campos
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    email = payload.get("email", "")
    phone = payload.get("phone", "")
    created_at = payload.get("date_created", datetime.datetime.utcnow().isoformat())

    location = payload.get("location", {})
    address = location.get("fullAddress", "")
    dealer_name = location.get("name", "SuperAutos Miami")

    # Construir XML en formato ADF
    adf_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<adf>
  <prospect>
    <requestdate>{created_at}</requestdate>
    <customer>
      <contact>
        <name part="first" type="individual">{first_name}</name>
        <name part="last" type="individual">{last_name}</name>
        <email>{email}</email>
        <phone type="voice">{phone}</phone>
      </contact>
    </customer>
    <provider>
      <name>{dealer_name}</name>
      <url>https://superautosmiami.com</url>
    </provider>
    <vehicle>
      <comments>
        Dirección registrada del cliente: {address}
      </comments>
    </vehicle>
  </prospect>
</adf>"""

    # Configurar y enviar el correo
    message = EmailMessage()
    message["Subject"] = "Lead Submission"
    message["From"] = "tucorreo@gmail.com"
    message["To"] = "dev@leadgrowthco.com"
    message.set_content(adf_xml)

    # Enviar email (Gmail SMTP)
    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=465,
        username="tucorreo@gmail.com",
        password="TU_APP_PASSWORD",  # Usa una App Password si tienes 2FA
        use_tls=True
    )
    print("📨 Lead enviado por correo exitosamente.")
    return {"status": "ok", "message": "Lead enviado correctamente a AutoRaptor"}