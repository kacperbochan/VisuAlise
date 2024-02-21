import requests

URL = "http://127.0.0.1:8188/"

response = requests.post(URL)

if response.status_code == 200:
    data = response.json()
    print(data)
    # Process the data returned from the API
else:
    print("Error:", response.status_code)
