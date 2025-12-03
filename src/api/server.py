import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import uvicorn

# Configuration
DB_PATH = os.getenv("DB_PATH", "vpn_bot.db")
API_PORT = int(os.getenv("API_PORT", "8000"))

app = FastAPI(title="MMVPN API")

class UserStatus(BaseModel):
    uuid: str
    is_active: bool
    expiry_date: str
    data_limit_gb: float
    daily_usage_bytes: int
    protocol: str

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
            protocol=user['protocol']
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/")
async def root():
    return {"message": "MMVPN API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
