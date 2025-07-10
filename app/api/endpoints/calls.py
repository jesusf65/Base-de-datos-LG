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

    # Datos base
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    email = payload.get("email", "")
    phone = payload.get("phone", "")
    created_at = payload.get("date_created", datetime.datetime.utcnow().isoformat())
    location = payload.get("location", {})
    dealer_name = location.get("name", "SuperAutos Miami")

    # Variables especiales para etiquetas
    dp = payload.get("Do you have at least $1,500 for the down payment?")
    ssn_info = payload.get("Tienes Social Security y cuenta bancaria ?")
    credit = payload.get("How would you describe your current credit situation?")

    # Ajustar nombres si hay valores
    if dp and isinstance(dp, list) and dp[0]:
        first_name += f" (dp={dp[0]})"
    if ssn_info or (credit and isinstance(credit, list) and credit[0]):
        last_tags = []
        if ssn_info:
            last_tags.append(f"ssn_info={ssn_info}")
        if credit and credit[0]:
            last_tags.append(f"cs={credit[0]}")
        last_name += " (" + ", ".join(last_tags) + ")"

    # Comentarios
    comments = []
    if dp and isinstance(dp, list) and dp[0]:
        comments.append(f"¿Tiene al menos $1,500 de entrada?: {dp[0]}")
    dp_es = payload.get("Tienes $1,500 de entrada ?")
    if dp_es:
        comments.append(f"Tiene $1,500 de entrada: {dp_es}")
    if ssn_info:
        comments.append(f"¿Tiene SSN y cuenta bancaria?: {ssn_info}")
    if credit and isinstance(credit, list) and credit[0]:
        comments.append(f"Situación crediticia actual: {credit[0]}")
    comments.append("Enviado desde LeadGrowth")

    comment_text = "\n".join(comments)

    # XML ADF completo
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
      <company>LeadGrowth</company>
    </customer>
    <provider>
      <name>{dealer_name}</name>
      <url>https://superautosmiami.com</url>
      <comments>
        {comment_text}
      </comments>
    </provider>
    <vehicle>
      <comments>
        {comment_text}
      </comments>
    </vehicle>
  </prospect>
</adf>"""

    # Enviar por correo
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
        password="eeth brok amri kitb",  # ← App Password aquí
        use_tls=True
    )

    print("📨 Lead enviado por correo exitosamente.")
    return {"status": "ok", "message": "Lead enviado correctamente a AutoRaptor"}
