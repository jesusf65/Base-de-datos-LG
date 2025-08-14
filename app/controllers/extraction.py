import http.client

conn = http.client.HTTPSConnection("services.leadconnectorhq.com")
payload = ''
headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer <TOKEN>'
}
conn.request("GET", "/conversations/search?contactId=(aca va el id que se obtiene)", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))