from fastapi import Request, HTTPException
import requests
import json

import sys
import os
rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, rootdir)
with open(f'{rootdir}/services/configs.json') as f:
    config = json.load(f)

service_name = __file__.split(os.sep)[-2]
endpoint_path = service_name.lower()

AUTH_SERVER_URL = config["services"][service_name] + f"/{endpoint_path}/validate"

def create_verify_token_function(auth_server_url: str):
    async def verify_token_function(request: Request):
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        
        response = requests.get(auth_server_url, headers={"Authorization": token})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return response.json()  # Return user info
    return verify_token_function

verify_token = create_verify_token_function(AUTH_SERVER_URL)


#example usage
#@app.get("/secure-endpoint")
#async def secure_endpoint(user=Depends(verify_token)):
#    return {"message": "Access granted", "user": user}
