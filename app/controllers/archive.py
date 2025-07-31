from typing import Dict

def build_adf_xml(data: Dict[str, str]) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<adf>
  <prospect>
    <requestdate>{data["created_at"]}</requestdate>
    <customer>
      <contact>
        <name part="first" type="individual">{data["first_name"]}</name>
        <name part="middle" type="individual">from LeadGrowth</name>
        <name part="last" type="individual">{data["last_name"]}</name>
        <email>{data["email"]}</email>
        <phone type="voice">{data["phone"]}</phone>
      </contact>
    </customer>
    <comment>
      {data["comment_text"]}
    </comment>
    <provider>
      <name>LeadGrowthCo</name>
    </provider>
  </prospect>
</adf>"""

def get_lead_email_recipients():
    """Retorna la lista de emails donde se deben enviar los leads"""
    return [
        "eleads-super-autos-miami-19355@app.autoraptor.com",
        "diazrenep@gmail.com",
        "diazrenet@gmail.com",
        "496a49324e7a59324e7a6369@pcmailhook.com"
    ]


