import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://localhost:8000"

def request(method, path, data=None):
    url = BASE_URL + path
    headers = {'Content-Type': 'application/json'}
    data_bytes = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()}

print("--- Testing KV-MX9 Advanced API ---")

# 1. SET
print("\n[Testing SET]")
print(request("POST", "/set", {"key": "hero", "value": "batman"}))
print(request("POST", "/set", {"key": "temp_key", "value": "123", "ttl": 2}))

# 2. GET
print("\n[Testing GET]")
print("hero:", request("GET", "/get/hero"))
print("temp_key immediately:", request("GET", "/get/temp_key"))

print("Waiting for 3 seconds for TTL expiration...")
time.sleep(3)
print("temp_key after waiting:", request("GET", "/get/temp_key"))

# 3. DELETE
print("\n[Testing DELETE]")
print(request("DELETE", "/delete/hero"))
print("hero after delete:", request("GET", "/get/hero"))

print("\n--- Testing Finished ---")
