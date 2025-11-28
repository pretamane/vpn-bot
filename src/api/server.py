import sys
import os
import logging
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ocr_service import ocr_service
from services.payment_validator import payment_validator, InvalidReceiptError
from db.database import get_db_connection

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

@app.get("/")
def read_root():
    return {"message": "VPN Bot API is running. Go to /docs for Swagger UI."}

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
