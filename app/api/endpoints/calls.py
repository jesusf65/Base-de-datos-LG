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

    # Extraer datos principales
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    email = payload.get("email", "")
    phone = payload.get("phone", "")
    created_at = payload.get("date_created", datetime.datetime.utcnow().isoformat())

    location = payload.get("location", {})
    dealer_name = location.get("name", "SuperAutos Miami")

    # Construcción de comentarios personalizados
    extra_comments = []

    down_payment_en = payload.get("Do you have at least $1,500 for the down payment?")
    if down_payment_en and isinstance(down_payment_en, list):
        extra_comments.append(f"¿Tiene al menos $1,500 de entrada?: {down_payment_en[0]}")

    down_payment_es = payload.get("Tienes $1,500 de entrada ?")
    if down_payment_es:
        extra_comments.append(f"Tiene $1,500 de entrada: {down_payment_es}")

    ssn_info = payload.get("Tienes Social Security y cuenta bancaria ?")
    if ssn_info:
        extra_comments.append(f"¿Tiene SSN y cuenta bancaria?: {ssn_info}")

    credit_situation = payload.get("How would you describe your current credit situation?")
    if credit_situation and isinstance(credit_situation, list):
        extra_comments.append(f"Situación crediticia actual: {credit_situation[0]}")

    # Comentarios combinados
    comment_text = "\n".join(extra_comments) if extra_comments else "Sin información adicional."

    # Crear XML formato ADF
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
        {comment_text},"nota agregada Hardcode"
      </comments>
    </vehicle>
  </prospect>
</adf>"""

    # Enviar correo con el lead en formato ADF
    message = EmailMessage()
    message["Subject"] = "Lead Submission"
    message["From"] = "dev@leadgrowthco.com"
    message["To"] = "eleads-super-autos-miami-19355@app.autoraptor.com"
    message.set_content(adf_xml)

    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=465,
        username="dev@leadgrowthco.com",
        password="eeth brok amri kitb",  # Tu App Password
        use_tls=True
    )

    print("📨 Lead enviado por correo exitosamente.")
    return {"status": "ok", "message": "Lead enviado correctamente a AutoRaptor"}
