# from typing import Dict, Any

# def parse_lead_payload(payload: Dict[str, Any]) -> Dict[str, str]:
#     first_name = payload.get("first_name", "")
#     last_name = payload.get("last_name", "")
#     email = payload.get("email", "")
#     phone = payload.get("phone", "")
#     created_at = payload.get("date_created")
#     location = payload.get("location", {})
#     dealer_name = location.get("name", "SuperAutos Miami")

#     # Extras
#     dp = payload.get("Do you have at least $1,500 for the down payment?")
#     ssn_info = payload.get("Tienes Social Security y cuenta bancaria ?")
#     credit = payload.get("How would you describe your current credit situation?")

#     dp_str = f"dp={dp[0]}" if dp and isinstance(dp, list) else ""
#     ssn_str = f"ssn={ssn_info}" if ssn_info else ""
#     cs_str = f"cs={credit[0]}" if credit and isinstance(credit, list) else ""

#     # Nombre modificado
#     if dp_str:
#         first_name += f" ({dp_str})"
#     if ssn_str or cs_str:
#         last_name += " (" + ", ".join(filter(None, [ssn_str, cs_str])) + ")"

#     # Comentarios
#     comments = []
#     if dp_str:
#         comments.append(f"¿Tiene al menos $1,500 de entrada?: {dp[0]}")
#     if ssn_info:
#         comments.append(f"¿Tiene SSN y cuenta bancaria?: {ssn_info}")
#     if credit:
#         comments.append(f"Situación crediticia actual: {credit[0]}")
#     comments.append("Enviado desde LeadGrowth")
#     comment_text = "\n".join(comments)

#     return {
#         "first_name": first_name,
#         "last_name": last_name,
#         "email": email,
#         "phone": phone,
#         "created_at": created_at,
#         "dealer_name": dealer_name,
#         "comment_text": comment_text,
#     }
