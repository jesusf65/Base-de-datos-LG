# from typing import Dict

# def build_adf_xml(data: Dict[str, str]) -> str:
#     return f"""<?xml version="1.0" encoding="utf-8"?>
# <adf>
#   <prospect>
#     <requestdate>{data["created_at"]}</requestdate>
#     <customer>
#       <contact>
#         <name part="first" type="individual">{data["first_name"]}</name>
#         <name part="middle" type="individual">from LeadGrowth</name>
#         <name part="last" type="individual">{data["last_name"]}</name>
#         <email>{data["email"]}</email>
#         <phone type="voice">{data["phone"]}</phone>
#       </contact>
#       <comments>
#         {data["comment_text"]}
#       </comments>
#     </customer>
#     <provider>
#       <name>{data["dealer_name"]}</name>
#       <url>https://superautosmiami.com</url>
#       <comments>
#         {data["comment_text"]}
#       </comments>
#     </provider>
#     <vehicle>
#       <comments>
#         {data["comment_text"]}
#       </comments>
#     </vehicle>
#   </prospect>
# </adf>"""