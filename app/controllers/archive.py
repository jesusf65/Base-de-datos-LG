from typing import Dict

def build_adf_xml(data: Dict[str, str]) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<?adf version="1.0"?>
<adf>
  <prospect>
    <requestdate>{data["created_at"]}</requestdate>
    <vendor>
      <id>8127727@leadsprod.dealercenter.net</id>
    </vendor>
    <provider>
      <name>LeadGrowthCo</name>
    </provider>
    <customer>
      <contact>
        <name part="first" type="individual">{data["first_name"]}</name>
        <name part="middle" type="individual">from LeadGrowth</name>
        <name part="last" type="individual">{data["last_name"]}</name>
        <email>{data["email"]}</email>
        <phone type="voice">{data["phone"]}</phone>
      </contact>
      <comments>{data["comment_text"]}</comments>
    </customer>
  </prospect>
</adf>"""


def get_lead_email_recipients():
    """Retorna la lista de emails donde se deben enviar los leads"""
    return [
        "8127727@leadsprod.dealercenter.net" 
    ]


