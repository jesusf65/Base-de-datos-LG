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

    # Variables especiales para etiquetar nombre y apellido
    dp = payload.get("Do you have at least $1,500 for the down payment?")
    dp_str = f"dp={dp[0]}" if dp and isinstance(dp, list) else ""

    ssn_info = payload.get("Tienes Social Security y cuenta bancaria ?")
    ssn_str = f"ssn={ssn_info}" if ssn_info else ""

    credit = payload.get("How would you describe your current credit situation?")
    cs_str = f"cs={credit[0]}" if credit and isinstance(credit, list) else ""

    # Ajustar nombres con etiquetas si aplica
    if dp_str:
        first_name += f" ({dp_str})"
    if ssn_str or cs_str:
        last_name += " (" + ", ".join(filter(None, [ssn_str, cs_str])) + ")"

    # Comentarios combinados para enviar
    comments = []
    if dp_str:
        comments.append(f"¿Tiene al menos $1,500 de entrada?: {dp[0]}")
    if ssn_info:
        comments.append(f"¿Tiene SSN y cuenta bancaria?: {ssn_info}")
    if credit:
        comments.append(f"Situación crediticia actual: {credit[0]}")

    if comments:
        comments.append("Enviado desde LeadGrowth")
        comment_text = "\n".join(comments)
    else:
        comment_text = "Enviado desde LeadGrowth"

    # Construir ADF XML
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
        {comment_text}
      </comments>
    </vehicle>
  </prospect>
</adf>"""

    # Enviar email
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
        password="eeth brok amri kitb",
        use_tls=True
    )

    print("📨 Lead enviado por correo exitosamente.")
    return {"status": "ok", "message": "Lead enviado correctamente a AutoRaptor"}
