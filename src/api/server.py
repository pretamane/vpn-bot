import sqlite3
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import os
import uvicorn
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests
from src.db.database import get_user_by_email, add_user, get_user

# Configuration
DB_PATH = os.getenv("DB_PATH", "vpn_bot.db")
API_PORT = int(os.getenv("API_PORT", "8000"))
# CLIENT_ID should be loaded from env or config, but for now we can accept any valid token for this app
# In production, you MUST verify the aud claim matches your client ID.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") 

app = FastAPI(title="MMVPN API")

class UserStatus(BaseModel):
    uuid: str
    is_active: bool
    expiry_date: str
    data_limit_gb: float
    daily_usage_bytes: int
    protocol: str

class GoogleLoginRequest(BaseModel):
    token: str

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/api/auth/google")
async def google_login(request: GoogleLoginRequest):
    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(request.token, requests.Request(), GOOGLE_CLIENT_ID)

        email = id_info.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Token does not contain email")
            
        # Check if user exists
        user = get_user_by_email(email)
        
        if user:
            user_uuid = user['uuid']
        else:
            # Create new user
            user_uuid = str(uuid.uuid4())
            # Default values for new users
            success = add_user(
                uuid=user_uuid,
                telegram_id=0, # No telegram ID for Google users initially
                username=email.split('@')[0],
                email=email,
                protocol='vless', # Default to VLESS for app users
                expiry_days=30,
                is_premium=False
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create user")

        return {"uuid": user_uuid, "email": email}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status/{uuid}", response_model=UserStatus)
async def get_user_status(uuid: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query for the user
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return UserStatus(
            uuid=user['uuid'],
            is_active=bool(user['is_active']),
            expiry_date=user['expiry_date'],
            data_limit_gb=user['data_limit_gb'],
            daily_usage_bytes=user['daily_usage_bytes'],
            protocol=user['protocol'] if user['protocol'] else 'ss'
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/")
async def root():
    return {"message": "MMVPN API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
