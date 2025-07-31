import httpx
import os
import asyncio
from app.controllers.archive import get_lead_email_recipients
RESEND_API_KEY = "RESEND_API_KEY"  # 👈 Reemplaza con tu clave de API de Resend
  # Asegúrate de definirla en tu entorno o .env

async def send_adf_email(adf_xml: str, to_email: str):
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "from": "dev@leadgrowthco.net",     # 👈 Este debe coincidir con el dominio verificado
        "to": [to_email],                    # 👈 ¡Siempre en lista!
        "subject": "Lead Submission",
        "text": adf_xml                      # También puedes usar "html": si es HTML
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.resend.com/emails", headers=headers, json=data)

        # 🧪 Imprimir el error para depurar
        if response.status_code >= 400:
            print("❌ Error al enviar con Resend:")
            print("Status:", response.status_code)
            print("Detalles:", response.text)

        response.raise_for_status()
        
async def send_lead_to_multiple_recipients(adf_xml: str):
    """
    Envía el lead a todos los destinatarios configurados con control de rate limit
    """
    recipients = get_lead_email_recipients()
    
    successful_sends = []
    failed_sends = []
    
    for i, email in enumerate(recipients):
        try:
            # Agregar delay entre envíos para evitar rate limit (excepto el primero)
            if i > 0:
                await asyncio.sleep(0.6)  # 600ms de delay = ~1.6 requests/second

            await send_adf_email(adf_xml, email)
            successful_sends.append(email)
            print(f"✅ Lead enviado exitosamente a: {email}")

        except Exception as e:
            failed_sends.append({"email": email, "error": str(e)})
            print(f"❌ Error enviando a {email}: {str(e)}")
    
    # Log resumen
    total_recipients = len(recipients)
    success_count = len(successful_sends)
    failure_count = len(failed_sends)
    
    print(f"📨 Resumen: {success_count}/{total_recipients} exitosos, {failure_count} fallidos")
    
    return {
        "total_recipients": total_recipients,
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "success_rate": success_count / total_recipients if total_recipients > 0 else 0
    }

