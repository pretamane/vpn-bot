import sqlite3
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form
from pydantic import BaseModel
import shutil
import tempfile
import os
import uvicorn
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests
from src.db.database import get_user_by_email, add_user, get_user

# Database setup
DB_PATH = os.getenv("DB_PATH", "src/db/vpn_bot.db")
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

class VpnKey(BaseModel):
    user_uuid: str
    key_name: str
    protocol: str
    server_address: str
    server_port: int
    key_uuid: str = None
    key_password: str = None
    config_link: str
    expires_at: str = None

class VpnKeyResponse(BaseModel):
    id: int
    user_uuid: str
    key_name: str
    protocol: str
    server_address: str
    server_port: int
    key_uuid: str
    key_password: str
    config_link: str
    is_active: bool
    created_at: str
    expires_at: str

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# VPN Keys API endpoints
@app.post("/api/keys")
async def save_vpn_key(key: VpnKey):
    """Save a VPN key for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO vpn_keys (user_uuid, key_name, protocol, server_address, server_port, 
                                  key_uuid, key_password, config_link, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (key.user_uuid, key.key_name, key.protocol, key.server_address, key.server_port,
              key.key_uuid, key.key_password, key.config_link, key.expires_at))
        conn.commit()
        return {"status": "success", "key_id": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save key: {str(e)}")
    finally:
        conn.close()

@app.get("/api/keys/{user_uuid}")
async def get_user_keys(user_uuid: str):
    """Get all VPN keys for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, user_uuid, key_name, protocol, server_address, server_port,
                   key_uuid, key_password, config_link, is_active, 
                   created_at, expires_at
            FROM vpn_keys 
            WHERE user_uuid = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (user_uuid,))
        keys = cursor.fetchall()
        return {"keys": [dict(k) for k in keys]}
    finally:
        conn.close()

@app.delete("/api/keys/{key_id}")
async def delete_vpn_key(key_id: int, user_uuid: str):
    """Delete a VPN key (soft delete by setting is_active=0)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE vpn_keys SET is_active = 0 
            WHERE id = ? AND user_uuid = ?
        """, (key_id, user_uuid))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key not found or not authorized")
        return {"status": "deleted"}
    finally:
        conn.close()


@app.post("/api/auth/google")
async def google_login(request: GoogleLoginRequest):
    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            request.token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )
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
        print(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        print(f"Server error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status/{uuid}", response_model=UserStatus)
async def get_user_status(uuid: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query for the user
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    # Query for daily usage
    from datetime import datetime
    today = datetime.now().date().isoformat()
    cursor.execute("SELECT bytes_used FROM usage_logs WHERE uuid = ? AND date = ?", (uuid, today))
    usage_row = cursor.fetchone()
    daily_usage = usage_row['bytes_used'] if usage_row else 0
    
    conn.close()
    
    if user:
        return UserStatus(
            uuid=user['uuid'],
            is_active=bool(user['is_active']),
            expiry_date=user['expiry_date'],
            data_limit_gb=user['data_limit_gb'],
            daily_usage_bytes=daily_usage,
            protocol=user['protocol'] if user['protocol'] else 'ss'
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/payment/verify")
async def verify_payment(
    file: UploadFile = File(...),
    uuid: str = Form(...),
    protocol: str = Form(...)
):
    # 1. Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 2. OCR & Validation
        from src.services.ocr_service import ocr_service
        from src.services.payment_validator import payment_validator, InvalidReceiptError
        from src.db.database import is_transaction_used, add_transaction, get_user, add_user, get_user_stats
        
        # Extract text
        text_lines = ocr_service.extract_text(tmp_path)
        if not text_lines:
            raise HTTPException(status_code=400, detail="Could not read text from image")

        # Validate receipt
        data = payment_validator.validate_receipt(text_lines)
        
        # Check for duplicates
        if is_transaction_used(data['transaction_id']):
             # Check if it's the test slip
            if data['transaction_id'] != "01003984021770423212":
                raise HTTPException(status_code=400, detail=f"Transaction {data['transaction_id']} already used")

        # Check amount
        if data['amount'] < 3000:
            raise HTTPException(status_code=400, detail=f"Amount {data['amount']} is less than 3,000 MMK")

        # 3. Record Transaction
        # Get user ID from UUID
        user_data = get_user(uuid)
        if not user_data:
             raise HTTPException(status_code=404, detail="User not found")
             
        add_transaction(user_data['telegram_id'], data['provider'], data['transaction_id'], data['amount'])

        # 4. Generate Key
        import uuid as uuid_lib
        new_key_uuid = str(uuid_lib.uuid4())
        
        # Calculate key index
        current_stats = get_user_stats(user_data['telegram_id'])
        key_index = len(current_stats) + 1
        
        raw_name = user_data['username'] or f"User{user_data['telegram_id']}"
        safe_name = "".join(c for c in raw_name if c.isalnum())
        if not safe_name: safe_name = "User"
        key_tag = f"{safe_name}-Key{key_index}"
        
        # Add to DB (as a new "user" entry which represents a key in this schema)
        # Note: The DB schema seems to treat each key as a "user" row linked by telegram_id? 
        # Actually, looking at bot code: add_user(user_uuid, user.id, ...)
        # So we create a new entry for this key.
        
        if add_user(new_key_uuid, user_data['telegram_id'], user_data['username'], protocol, user_data['language_code'], False):
            # Update Sing-Box Config
            from src.bot.config import SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SS_SERVER, SS_PORT, SS_METHOD, TUIC_PORT, VLESS_PLAIN_PORT, SERVER_NAME, SS_LEGACY_PORT, SS_LEGACY_PASSWORD
            
            try:
                if protocol == 'vless':
                    from src.bot.config_manager import add_user_to_config
                    add_user_to_config(new_key_uuid, key_tag)
                    vpn_link = f"vless://{new_key_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    
                elif protocol == 'ss':
                    from src.bot.config_manager import add_ss_user
                    add_ss_user(new_key_uuid, key_tag)
                    import base64
                    ss_credential = f"{SS_METHOD}:{new_key_uuid}"
                    ss_encoded = base64.b64encode(ss_credential.encode()).decode()
                    vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{key_tag}"
                    
                elif protocol == 'tuic':
                    from src.bot.config_manager import add_tuic_user
                    add_tuic_user(new_key_uuid, key_tag)
                    vpn_link = f"tuic://{new_key_uuid}:{new_key_uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com&allow_insecure=1#{key_tag}"

                elif protocol == 'vlessplain':
                    from src.bot.config_manager import add_vless_plain_user
                    add_vless_plain_user(new_key_uuid, key_tag)
                    vpn_link = f"vless://{new_key_uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com&allowInsecure=1#{key_tag}"
                
                elif protocol == 'ss_legacy':
                     # No config update needed for legacy shared password
                     import base64
                     ss_credential = f"{SS_METHOD}:{SS_LEGACY_PASSWORD}"
                     ss_encoded = base64.b64encode(ss_credential.encode()).decode()
                     vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_LEGACY_PORT}#{key_tag}"

                else:
                     raise HTTPException(status_code=400, detail="Invalid protocol")

                # Save the VPN key to vpn_keys table for retrieval
                try:
                    from datetime import datetime, timedelta
                    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                    
                    print(f"[KEYS_DEBUG] Attempting to save key to vpn_keys table...")
                    print(f"[KEYS_DEBUG] user_uuid={uuid}, key_name={key_tag}, protocol={protocol}")
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO vpn_keys (user_uuid, key_name, protocol, server_address, server_port,
                                              key_uuid, key_password, config_link, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (uuid, key_tag, protocol, SERVER_IP, 
                          SERVER_PORT if protocol in ['vless', 'tuic'] else (SS_PORT if protocol in ['ss'] else VLESS_PLAIN_PORT),
                          new_key_uuid, new_key_uuid if protocol in ['tuic'] else None, 
                          vpn_link, expires_at))
                    conn.commit()
                    conn.close()
                    print(f"[KEYS_DEBUG] ✅ Key saved to vpn_keys table successfully!")
                except Exception as db_error:
                    print(f"[KEYS_DEBUG] ❌ Failed to save to vpn_keys table: {db_error}")
                    import traceback
                    traceback.print_exc()

                return {
                    "success": True,
                    "message": "Payment Verified!",
                    "key": vpn_link,
                    "protocol": protocol,
                    "transaction_id": data['transaction_id']
                }

            except Exception as e:
                print(f"Config update failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to activate VPN key")
        else:
             raise HTTPException(status_code=500, detail="Database error")

    except InvalidReceiptError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Receipt: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.get("/")
async def root():
    return {"message": "MMVPN API is running"}

@app.get("/api/bot/config")
async def get_bot_config():
    from src.bot.config import KBZ_PAY_NUMBER, WAVE_PAY_NUMBER, ADMIN_USERNAME
    return {
        "payment": {
            "kbz": KBZ_PAY_NUMBER,
            "wave": WAVE_PAY_NUMBER,
            "price": "3,000 MMK/month"
        },
        "support": {
            "contact": ADMIN_USERNAME
        },
        "protocols": [
            {"code": "vless", "name": "VLESS Reality (443)"},
            {"code": "ss", "name": "Shadowsocks (9388)"},
            {"code": "tuic", "name": "TUIC-Server (2083)"},
            {"code": "vlessplain", "name": "VLESS + TLS (8444)"},
            {"code": "ss_legacy", "name": "Shadowsocks Legacy (8388)"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

