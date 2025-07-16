#import aiosmtplib
#from email.message import EmailMessage



#async def send_adf_email(adf_xml: str, to_email: str):
 #   message = EmailMessage()
  #  message["Subject"] = "Lead Submission"
    #message["From"] = "dev@leadgrowthco.com"
    #message["To"] = to_email
  #  message.set_content(adf_xml)
#
 #   await aiosmtplib.send(
     #   message,
 #       hostname="smtp.gmail.com",
  #      port=465,
   #     username="dev@leadgrowthco.com",
    #    password="eeth brok amri kitb",
     #   use_tls=True
    #)