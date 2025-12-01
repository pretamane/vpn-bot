import sys
import os
import logging
import shutil
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ocr_service import ocr_service
from services.payment_validator import payment_validator, InvalidReceiptError
from db.database import get_db_connection
from bot.config import SERVER_IP, SERVER_PORT, PUBLIC_KEY, SHORT_ID, SERVER_NAME, SS_SERVER, SS_PORT, SS_METHOD, TUIC_PORT, VLESS_PLAIN_PORT

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(
    title="VPN Bot Payment API",
    description="API for testing OCR and Payment Validation logic.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidationResult(BaseModel):
    provider: str
    transaction_id: str
    amount: float
    status: str
    message: str

class KeyInfo(BaseModel):
    uuid: str
    telegram_id: int
    username: Optional[str]
    protocol: str
    is_active: bool
    created_at: str
    expiry_date: str
    vpn_link: str

@app.get("/")
def read_root():
    return {"message": "VPN Bot API is running. Go to /docs for Swagger UI or /viewer for Key Viewer."}

@app.get("/viewer", response_class=HTMLResponse)
async def key_viewer():
    """Serve the key viewer HTML interface."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "key_viewer.html")
    try:
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Key viewer not found")

@app.get("/keys")
def get_all_keys():
    """Get all VPN keys with their details."""
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT u.uuid, u.telegram_id, u.username, u.protocol, u.is_active, 
               u.created_at, u.expiry_date, u.data_limit_gb, ul.bytes_used as daily_usage_bytes
        FROM users u
        LEFT JOIN usage_logs ul ON u.uuid = ul.uuid AND ul.date = DATE('now')
        ORDER BY u.created_at DESC
    ''').fetchall()
    conn.close()
    
    keys = []
    for row in rows:
        uuid = row['uuid']
        protocol = row['protocol']
        username = row['username'] or f"User{row['telegram_id']}"
        
        # Generate VPN link based on protocol
        if protocol == 'vless':
            vpn_link = f"vless://{uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{username}"
        elif protocol == 'tuic' or protocol == 'admin_tuic':
            # TUIC uses UUID as password
            vpn_link = f"tuic://{uuid}:{uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#{username}"
        elif protocol == 'vlessplain':
            vpn_link = f"vless://{uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com#{username}"
        else:  # shadowsocks
            ss_credential = f"{SS_METHOD}:{uuid}"
            ss_encoded = base64.b64encode(ss_credential.encode()).decode()
            vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{username}"
        
        keys.append({
            'uuid': uuid,
            'telegram_id': row['telegram_id'],
            'username': row['username'],
            'protocol': protocol,
            'is_active': bool(row['is_active']),
            'created_at': row['created_at'],
            'expiry_date': row['expiry_date'],
            'vpn_link': vpn_link,
            'usage_gb': row['daily_usage_bytes'] / (1024**3) if row['daily_usage_bytes'] else 0,
            'limit_gb': row['data_limit_gb']
        })
    
    return {"keys": keys, "count": len(keys)}

@app.get("/keys/{uuid}")
def get_key_by_uuid(uuid: str):
    """Get a specific key by UUID."""
    conn = get_db_connection()
    row = conn.execute('''
        SELECT u.uuid, u.telegram_id, u.username, u.protocol, u.is_active, 
               u.created_at, u.expiry_date, u.data_limit_gb, ul.bytes_used as daily_usage_bytes
        FROM users u
        LEFT JOIN usage_logs ul ON u.uuid = ul.uuid AND ul.date = DATE('now')
        WHERE u.uuid = ?
    ''', (uuid,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    
    protocol = row['protocol']
    username = row['username'] or f"User{row['telegram_id']}"
    
    # Generate VPN link
    # Generate VPN link
    if protocol == 'vless':
        vpn_link = f"vless://{uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{username}"
    elif protocol == 'tuic' or protocol == 'admin_tuic':
        vpn_link = f"tuic://{uuid}:{uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#{username}"
    elif protocol == 'vlessplain':
        vpn_link = f"vless://{uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com#{username}"
    else:
        ss_credential = f"{SS_METHOD}:{uuid}"
        ss_encoded = base64.b64encode(ss_credential.encode()).decode()
        vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{username}"
    
    return {
        'uuid': uuid,
        'telegram_id': row['telegram_id'],
        'username': row['username'],
        'protocol': protocol,
        'is_active': bool(row['is_active']),
        'created_at': row['created_at'],
        'expiry_date': row['expiry_date'],
        'vpn_link': vpn_link,
        'usage_gb': row['daily_usage_bytes'] / (1024**3) if row['daily_usage_bytes'] else 0,
        'limit_gb': row['data_limit_gb']
    }

@app.post("/verify-slip", response_model=ValidationResult)
async def verify_slip(file: UploadFile = File(...)):
    """
    Upload a payment slip image to test OCR and Validation.
    """
    temp_file = f"temp_{file.filename}"
    try:
        # Save uploaded file
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. OCR
        logger.info(f"Processing {file.filename}...")
        text_lines = ocr_service.extract_text(temp_file)
        
        if not text_lines:
            raise HTTPException(status_code=400, detail="Could not extract text from image.")
            
        # 2. Validate
        try:
            data = payment_validator.validate_receipt(text_lines)
            return ValidationResult(
                provider=data['provider'],
                transaction_id=data['transaction_id'],
                amount=data['amount'],
                status="valid",
                message="Receipt is valid."
            )
        except InvalidReceiptError as e:
            return ValidationResult(
                provider="Unknown",
                transaction_id="Unknown",
                amount=0.0,
                status="invalid",
                message=str(e)
            )
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@app.get("/transactions")
def get_transactions():
    """
    List recent transactions from the database.
    """
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM payment_transactions ORDER BY created_at DESC LIMIT 50').fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

