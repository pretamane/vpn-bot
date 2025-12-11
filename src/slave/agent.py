import json
import subprocess
import os
import secrets
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import logging

# Configuration
SINGBOX_CONFIG_PATH = "/etc/sing-box/config.json"
API_TOKEN = os.getenv("AGENT_TOKEN", "default-insecure-token")  # Should be set via env var
PORT = 8000

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MMVPN Slave Agent")

# Models
class User(BaseModel):
    uuid: str
    email: str
    limit_mbps: float = 0

class RemoveUserRequest(BaseModel):
    uuid: str

# Auth
async def verify_token(x_token: str = Header(...)):
    if x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Token")

# Helpers
def load_config():
    try:
        with open(SINGBOX_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config not found at {SINGBOX_CONFIG_PATH}")
        raise HTTPException(status_code=500, detail="Config file not found")

def save_config(config):
    temp_path = "/tmp/singbox_config.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(["sudo", "cp", temp_path, SINGBOX_CONFIG_PATH], check=True)
        subprocess.run(["rm", temp_path], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

def reload_service():
    try:
        subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True)
        logger.info("Service reloaded")
    except subprocess.CalledProcessError:
        try:
            subprocess.run(["sudo", "systemctl", "restart", "sing-box"], check=True)
            logger.info("Service restarted")
        except Exception as e:
            logger.error(f"Failed to reload/restart service: {e}")
            raise HTTPException(status_code=500, detail="Failed to reload service")

# Endpoints
@app.post("/user", dependencies=[Depends(verify_token)])
async def add_user(user: User):
    config = load_config()
    target_tag = "vless-in"
    
    # Simple logic: Find the first VLESS inbound
    target_inbound = None
    for inbound in config['inbounds']:
        if inbound['type'] == 'vless':
            target_inbound = inbound
            break
            
    if not target_inbound:
        raise HTTPException(status_code=500, detail="No VLESS inbound found")
        
    users = target_inbound.get('users', [])
    
    # Check if exists
    for u in users:
        if u['uuid'] == user.uuid:
            return {"status": "exists", "message": "User already exists"}
            
    users.append({
        "uuid": user.uuid,
        "flow": "xtls-rprx-vision",
        "name": user.email
    })
    target_inbound['users'] = users
    
    save_config(config)
    reload_service()
    
    logger.info(f"Added user {user.email} ({user.uuid})")
    return {"status": "success", "message": f"User {user.email} added"}

@app.delete("/user/{uuid}", dependencies=[Depends(verify_token)])
async def remove_user(uuid: str):
    config = load_config()
    
    found = False
    for inbound in config['inbounds']:
        if 'users' in inbound:
            original_len = len(inbound['users'])
            inbound['users'] = [u for u in inbound['users'] if u.get('uuid') != uuid]
            if len(inbound['users']) < original_len:
                found = True
                
    if found:
        save_config(config)
        reload_service()
        logger.info(f"Removed user {uuid}")
        return {"status": "success", "message": "User removed"}
    else:
        return {"status": "not_found", "message": "User not found"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
