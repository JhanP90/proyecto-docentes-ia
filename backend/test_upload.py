import requests

url = "http://127.0.0.1:8000/api/v1/hojas-vida/upload"
files = {'file': ('hoja.pdf', b'%PDF-1.4\n...', 'application/pdf')}
headers = {'accept': 'application/json'}
try:
    response = requests.post(url, files=files, headers=headers)
    print("Status Code:", response.status_code)
    print("Response text:", response.text)
except Exception as e:
    print("Error:", e)
