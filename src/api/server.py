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
from src.db.database import get_user_by_email, get_user_by_phone, add_user, get_user, get_daily_usage, is_in_grace_period, get_grace_period_remaining

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
    usage_percentage: float = 0.0  # Percentage of data used (0-100+)
    in_grace_period: bool = False  # Whether user is in 24h grace period
    grace_remaining_hours: float = 0.0  # Hours remaining in grace period
    warnings_sent: list = []  # List of warning thresholds triggered (e.g., ['30', '65'])

class GoogleLoginRequest(BaseModel):
    token: str

class PhoneLoginRequest(BaseModel):
    phone: str

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
            ORDER BY 
              CASE WHEN protocol = 'vless_limited' THEN 1 ELSE 0 END ASC,
              created_at DESC
        """, (user_uuid,))
        keys = cursor.fetchall()
        
        result_keys = []
        for k in keys:
            k_dict = dict(k)
            tag = "[Free]" if k['protocol'] == 'vless_limited' else "[Premium]"
            k_dict['key_name'] = f"{k['key_name']} {tag}"
            result_keys.append(k_dict)
            
        return {"keys": result_keys}
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
                protocol='account', # Placeholder protocol for account entry
                expiry_days=30,
                is_premium=False
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create user")

        # Check for existing keys (fetch ALL active keys)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT config_link, key_uuid, protocol, created_at FROM vpn_keys 
            WHERE user_uuid = ? AND is_active = 1
            ORDER BY 
              CASE WHEN protocol = 'vless_limited' THEN 1 ELSE 0 END ASC,
              created_at DESC
        """, (user_uuid,))
        existing_keys = cursor.fetchall()
        
        # Also fetch keys from users table (for old keys not in vpn_keys)
        # Include the main user_uuid as it might be an old valid key
        cursor.execute("""
            SELECT uuid, protocol, username, created_at FROM users 
            WHERE email = ? AND is_active = 1
        """, (email,))
        old_keys = cursor.fetchall()
        conn.close()

        vpn_key_links = []
        key_uuid_to_return = None
        vless_limited_found = False
        
        # Track added UUIDs to avoid duplicates
        added_uuids = set()

        # Smart Default Logic
        # 1. Collect all valid keys with their metadata
        all_valid_keys = []
        
        # Add existing keys from vpn_keys table
        if existing_keys:
            for k in existing_keys:
                if k['key_uuid'] not in added_uuids:
                    vpn_key_links.append(k['config_link'])
                    added_uuids.add(k['key_uuid'])
                    all_valid_keys.append({
                        'uuid': k['key_uuid'],
                        'protocol': k['protocol'],
                        'created_at': k['created_at'] if 'created_at' in k.keys() else '',
                        'source': 'vpn_keys'
                    })

        # Add old keys from users table
        if old_keys:
            from src.bot.config import SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SS_SERVER, SS_PORT, SS_METHOD, TUIC_PORT, VLESS_PLAIN_PORT, SERVER_NAME, SS_LEGACY_PORT, SS_LEGACY_PASSWORD, LIMITED_PORT
            import base64
            
            for k in old_keys:
                k_uuid = k['uuid']
                if k_uuid not in added_uuids:
                    # Reconstruct link
                    proto = k['protocol']
                    link = None
                    key_tag = k['username']
                    
                    if proto == 'vless':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    elif proto == 'vless_limited':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{LIMITED_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    elif proto == 'ss':
                        ss_credential = f"{SS_METHOD}:{k_uuid}"
                        ss_encoded = base64.b64encode(ss_credential.encode()).decode()
                        link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{key_tag}"
                    elif proto == 'tuic':
                        link = f"tuic://{k_uuid}:{k_uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com&allow_insecure=1#{key_tag}"
                    elif proto == 'vlessplain':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com&allowInsecure=1#{key_tag}"
                    
                    if link:
                        vpn_key_links.append(link)
                        added_uuids.add(k_uuid)
                        all_valid_keys.append({
                            'uuid': k_uuid,
                            'protocol': proto,
                            'created_at': k['created_at'] if 'created_at' in k.keys() else '',
                            'source': 'users'
                        })

        # 2. Determine Default Key (key_uuid_to_return)
        # Logic:
        # - If User has Premium Keys (not vless_limited) -> Return Most Recent Premium Key
        # - Else -> Return vless_limited Key (create if needed)
        
        premium_keys = [k for k in all_valid_keys if k['protocol'] != 'vless_limited']
        limited_keys = [k for k in all_valid_keys if k['protocol'] == 'vless_limited']
        
        if premium_keys:
            # User is PAID (has premium keys)
            # Return the first one (assuming list is ordered by created_at DESC from queries)
            # existing_keys was ordered by created_at DESC.
            # old_keys order is undefined but usually insertion order (older).
            # So the first item in premium_keys should be the most recent one from vpn_keys.
            key_uuid_to_return = premium_keys[0]['uuid']
            vless_limited_found = True # Treat as found so we don't auto-provision
        elif limited_keys:
            # User is FREE (only limited keys)
            key_uuid_to_return = limited_keys[0]['uuid']
            vless_limited_found = True
        else:
            # User has NO keys
            vless_limited_found = False
            key_uuid_to_return = None

        # If no vless_limited key exists, auto-provision one
        if not vless_limited_found and not key_uuid_to_return: # Only auto-provision if NO keys exist? Or if no vless_limited?
            # User requirement: "prioritize and return the vless_limited key... even if the user has created newer... keys"
            # If they have keys but none are vless_limited, should I create one?
            # Probably yes, if that's the "free tier" they expect.
            # But if they have paid keys, maybe they don't need it.
            # Let's stick to: if no vless_limited found, create it.
            pass # Fall through to auto-provision logic below
            
        if not vless_limited_found:
            # Auto-provision new vless_limited key
            try:
                import uuid as uuid_lib
                from src.db.database import get_user_stats
                from src.bot.config import SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_NAME, LIMITED_PORT
                from src.bot.config_manager import add_user_to_config
                
                new_key_uuid = str(uuid_lib.uuid4())
                key_uuid_to_return = new_key_uuid
                
                # Calculate key index (using 0 as telegram_id for google users if not set, or handle gracefully)
                # For now, we'll just use a timestamp-based tag to avoid collision if telegram_id is 0
                import time
                key_tag = f"User-{int(time.time())}"
                
                # Add to system (users table for key tracking)
                # vless_limited: 12 Mbps, 3 GB
                if add_user(new_key_uuid, 0, email.split('@')[0], 'vless_limited', 'en', False, speed_limit_mbps=12.0, data_limit_gb=3.0):
                    
                    # Add to Sing-Box Config
                    add_user_to_config(new_key_uuid, key_tag, limit_mbps=12.0)
                    
                    # Generate Link
                    vpn_key_link = f"vless://{new_key_uuid}@{SERVER_IP}:{LIMITED_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    
                    # Save to vpn_keys
                    from datetime import datetime, timedelta
                    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO vpn_keys (user_uuid, key_name, protocol, server_address, server_port,
                                              key_uuid, config_link, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (user_uuid, key_tag, 'vless_limited', SERVER_IP, LIMITED_PORT,
                          new_key_uuid, vpn_key_link, expires_at))
                    conn.commit()
                    conn.close()
                    print(f"[AUTO_PROVISION] Created new key for {email}")
                    
                    # Add the new key to the end of the list
                    vpn_key_links.append(vpn_key_link)
                    key_uuid_to_return = new_key_uuid

            except Exception as e:
                print(f"[AUTO_PROVISION] Failed: {e}")
                pass

        # Join all links with newlines
        final_key_string = "\n".join(vpn_key_links) if vpn_key_links else None

        return {"uuid": user_uuid, "email": email, "key": final_key_string, "key_uuid": key_uuid_to_return}

    except ValueError as e:
        print(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        print(f"Server error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/auth/phone")
async def phone_login(request: PhoneLoginRequest):
    try:
        phone = request.phone
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number required")
            
        # Check if user exists
        user = get_user_by_phone(phone)
        
        if user:
            user_uuid = user['uuid']
            email = user['email'] or f"{phone}@phone.com" # Fallback email
        else:
            # Create new user
            user_uuid = str(uuid.uuid4())
            email = f"{phone}@phone.com" # Placeholder email
            # Default values for new users
            success = add_user(
                uuid=user_uuid,
                telegram_id=0, 
                username=phone, # Use phone as username
                email=email,
                protocol='account', 
                expiry_days=30,
                is_premium=False,
                phone=phone
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create user")

        # Check for existing keys (fetch ALL active keys)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT config_link, key_uuid, protocol, created_at FROM vpn_keys 
            WHERE user_uuid = ? AND is_active = 1
            ORDER BY 
              CASE WHEN protocol = 'vless_limited' THEN 1 ELSE 0 END ASC,
              created_at DESC
        """, (user_uuid,))
        existing_keys = cursor.fetchall()
        
        # Also fetch keys from users table (for old keys not in vpn_keys)
        cursor.execute("""
            SELECT uuid, protocol, username, created_at FROM users 
            WHERE phone = ? AND is_active = 1
        """, (phone,))
        old_keys = cursor.fetchall()
        conn.close()

        vpn_key_links = []
        key_uuid_to_return = None
        vless_limited_found = False
        
        # Track added UUIDs to avoid duplicates
        added_uuids = set()

        # Smart Default Logic
        all_valid_keys = []
        
        # Add existing keys from vpn_keys table
        if existing_keys:
            for k in existing_keys:
                if k['key_uuid'] not in added_uuids:
                    vpn_key_links.append(k['config_link'])
                    added_uuids.add(k['key_uuid'])
                    all_valid_keys.append({
                        'uuid': k['key_uuid'],
                        'protocol': k['protocol'],
                        'created_at': k['created_at'] if 'created_at' in k.keys() else '',
                        'source': 'vpn_keys'
                    })

        # Add old keys from users table
        if old_keys:
            from src.bot.config import SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SS_SERVER, SS_PORT, SS_METHOD, TUIC_PORT, VLESS_PLAIN_PORT, SERVER_NAME, SS_LEGACY_PORT, SS_LEGACY_PASSWORD, LIMITED_PORT
            import base64
            
            for k in old_keys:
                k_uuid = k['uuid']
                if k_uuid not in added_uuids:
                    # Reconstruct link
                    proto = k['protocol']
                    link = None
                    key_tag = k['username']
                    
                    if proto == 'vless':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    elif proto == 'vless_limited':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{LIMITED_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    elif proto == 'ss':
                        ss_credential = f"{SS_METHOD}:{k_uuid}"
                        ss_encoded = base64.b64encode(ss_credential.encode()).decode()
                        link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{key_tag}"
                    elif proto == 'tuic':
                        link = f"tuic://{k_uuid}:{k_uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com&allow_insecure=1#{key_tag}"
                    elif proto == 'vlessplain':
                        link = f"vless://{k_uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com&allowInsecure=1#{key_tag}"
                    
                    if link:
                        vpn_key_links.append(link)
                        added_uuids.add(k_uuid)
                        all_valid_keys.append({
                            'uuid': k_uuid,
                            'protocol': proto,
                            'created_at': k['created_at'] if 'created_at' in k.keys() else '',
                            'source': 'users'
                        })

        premium_keys = [k for k in all_valid_keys if k['protocol'] != 'vless_limited']
        limited_keys = [k for k in all_valid_keys if k['protocol'] == 'vless_limited']
        
        if premium_keys:
            key_uuid_to_return = premium_keys[0]['uuid']
            vless_limited_found = True
        elif limited_keys:
            key_uuid_to_return = limited_keys[0]['uuid']
            vless_limited_found = True
        else:
            vless_limited_found = False
            key_uuid_to_return = None

        if not vless_limited_found:
            # Auto-provision new vless_limited key
            try:
                import uuid as uuid_lib
                from src.bot.config import SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_NAME, LIMITED_PORT
                from src.bot.config_manager import add_user_to_config
                
                new_key_uuid = str(uuid_lib.uuid4())
                key_uuid_to_return = new_key_uuid
                
                import time
                key_tag = f"User-{int(time.time())}"
                
                # Add to system (users table for key tracking)
                if add_user(new_key_uuid, 0, phone, 'vless_limited', 'en', False, speed_limit_mbps=12.0, data_limit_gb=3.0, phone=phone):
                    
                    # Add to Sing-Box Config
                    add_user_to_config(new_key_uuid, key_tag, limit_mbps=12.0)
                    
                    # Generate Link
                    vpn_key_link = f"vless://{new_key_uuid}@{SERVER_IP}:{LIMITED_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    
                    # Save to vpn_keys
                    from datetime import datetime, timedelta
                    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO vpn_keys (user_uuid, key_name, protocol, server_address, server_port,
                                              key_uuid, config_link, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (user_uuid, key_tag, 'vless_limited', SERVER_IP, LIMITED_PORT,
                          new_key_uuid, vpn_key_link, expires_at))
                    conn.commit()
                    conn.close()
                    print(f"[AUTO_PROVISION] Created new key for {phone}")
                    
                    vpn_key_links.append(vpn_key_link)
                    key_uuid_to_return = new_key_uuid

            except Exception as e:
                print(f"[AUTO_PROVISION] Failed: {e}")
                pass

        final_key_string = "\n".join(vpn_key_links) if vpn_key_links else None

        return {"uuid": user_uuid, "email": email, "key": final_key_string, "key_uuid": key_uuid_to_return}

    except Exception as e:
        print(f"Server error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status/{user_uuid}")
async def get_user_status(user_uuid: str):
    print(f"\n========== STATUS API DEBUG ==========")
    print(f"[1] Incoming UUID: {user_uuid}")
    
    user = get_user(user_uuid)
    if not user:
        print(f"[ERROR] User NOT FOUND in database")
        raise HTTPException(status_code=404, detail="User not found")
    
    print(f"[2] User found: protocol={user['protocol']}, is_active={user['is_active']}")
    
    # Calculate usage
    # Calculate usage and aggregate limits/expiry from keys
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vpn_keys WHERE user_uuid = ? AND is_active = 1", (user_uuid,))
    linked_keys = cursor.fetchall()
    conn.close()
    
    print(f"[3] Linked keys found: {len(linked_keys)}")
    
    daily_usage = 0
    data_limit_gb = 0.0
    max_expiry = None
    
    if linked_keys:
        print(f"[4] Processing {len(linked_keys)} linked key(s)...")
        for k in linked_keys:
            daily_usage += get_daily_usage(k['key_uuid'])
            
            # Fetch key's data limit from users table (since keys are stored as users too)
            # Or we can store it in vpn_keys? vpn_keys doesn't have data_limit.
            # We need to fetch the "user" row corresponding to the key_uuid
            key_user_row = get_user(k['key_uuid'])
            if key_user_row:
                data_limit_gb += key_user_row['data_limit_gb'] or 0.0
            
            # Calculate max expiry
            key_expiry_str = k['expires_at']
            if key_expiry_str:
                try:
                    from datetime import datetime
                    key_expiry = datetime.fromisoformat(key_expiry_str)
                    if max_expiry is None or key_expiry > max_expiry:
                        max_expiry = key_expiry
                except:
                    pass
        
        # If we found keys, use the aggregated values
        # If data_limit is still 0 (shouldn't be), fallback to user's
        if data_limit_gb == 0:
             data_limit_gb = user['data_limit_gb'] or 5.0
             
        # Format max_expiry
        if max_expiry:
            expiry_date_str = max_expiry.isoformat()
        else:
             expiry_date_str = str(user['expiry_date'])

    else:
        # Fallback: check if this UUID itself has usage (legacy or single key)
        daily_usage = get_daily_usage(user_uuid)
        data_limit_gb = user['data_limit_gb'] or 5.0
        expiry_date_str = str(user['expiry_date'])

    # Check grace period
    user_dict = dict(user)
    in_grace_period = is_in_grace_period(user_dict)
    grace_remaining = None
    if in_grace_period:
        remaining = get_grace_period_remaining(user_dict)
        if remaining:
            grace_remaining = remaining.total_seconds() / 3600 # Hours
            
    # Format expiry date (remove microseconds)
    if '.' in expiry_date_str:
        expiry_date_str = expiry_date_str.split('.')[0]

    # Determine protocol to display
    display_protocol = user['protocol']
    if linked_keys:
        # Use the protocol of the most recently created key (or just the first one found)
        # Since we fetched all, let's pick the last one (assuming order or just picking one)
        # Ideally we should sort by created_at, but for now picking the last one in the list is a safe bet for "latest"
        display_protocol = linked_keys[-1]['protocol']
        print(f"[5] Using protocol from linked key: {display_protocol}")
    else:
        print(f"[5] Using user's default protocol: {display_protocol}")
    
    print(f"[6] Aggregated stats: usage={daily_usage}, limit={data_limit_gb}GB, expiry={expiry_date_str}")
    
    response_data = {
        "uuid": user['uuid'],
        "protocol": display_protocol,
        "isActive": user['is_active'] == 1,
        "dataLimitGb": data_limit_gb,
        "dailyUsageBytes": daily_usage,
        "expiryDate": expiry_date_str,
        "usagePercentage": (daily_usage / (data_limit_gb * 1024 * 1024 * 1024)) * 100,
        "inGracePeriod": in_grace_period,
        "graceRemainingHours": grace_remaining or 0
    }
    
    print(f"[7] Returning response: {response_data}")
    print(f"========================================\n")
    return response_data

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
        # Calculate key index (User-Specific)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vpn_keys WHERE user_uuid = ?", (uuid,))
        key_count = cursor.fetchone()[0]
        conn.close()
        
        key_index = key_count + 1
        
        raw_name = user_data['username'] or f"User{user_data['telegram_id']}"
        safe_name = "".join(c for c in raw_name if c.isalnum())
        if not safe_name: safe_name = "User"
        key_tag = f"{safe_name}-Key{key_index}"
        
        # Add to DB (as a new "user" entry which represents a key in this schema)
        # Note: The DB schema seems to treat each key as a "user" row linked by telegram_id? 
        # Actually, looking at bot code: add_user(user_uuid, user.id, ...)
        # So we create a new entry for this key.
        
        limit_mbps = 12.0 if protocol == 'vless_limited' else 0.0
        data_limit_gb = 3.0 if protocol == 'vless_limited' else 5.0  # 3GB for VLESS Limited, 5GB default for others
        
        if add_user(new_key_uuid, user_data['telegram_id'], user_data['username'], protocol, user_data['language_code'], False, speed_limit_mbps=limit_mbps, data_limit_gb=data_limit_gb):
            # Update Sing-Box Config
            from src.bot.config import SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SS_SERVER, SS_PORT, SS_METHOD, TUIC_PORT, VLESS_PLAIN_PORT, SERVER_NAME, SS_LEGACY_PORT, SS_LEGACY_PASSWORD, LIMITED_PORT
            
            try:
                if protocol == 'vless':
                    from src.bot.config_manager import add_user_to_config
                    add_user_to_config(new_key_uuid, key_tag, limit_mbps=0)
                    vpn_link = f"vless://{new_key_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                
                elif protocol == 'vless_limited':
                    from src.bot.config_manager import add_user_to_config
                    add_user_to_config(new_key_uuid, key_tag, limit_mbps=12.0)
                    # Use LIMITED_PORT (10001) for the link
                    vpn_link = f"vless://{new_key_uuid}@{SERVER_IP}:{LIMITED_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
                    
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
                          SERVER_PORT if protocol in ['vless', 'tuic'] else (LIMITED_PORT if protocol == 'vless_limited' else (SS_PORT if protocol in ['ss'] else VLESS_PLAIN_PORT)),
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
            {"code": "vless", "name": "VLESS Reality (Unlimited)"},
            {"code": "vless_limited", "name": "VLESS Limited (12 Mbps)"},
            {"code": "ss", "name": "Shadowsocks (9388)"},
            {"code": "tuic", "name": "TUIC-Server (2083)"},
            {"code": "vlessplain", "name": "VLESS + TLS (8444)"},
            {"code": "ss_legacy", "name": "Shadowsocks Legacy (8388)"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

