import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

FABRICO_BE_URL = os.getenv("FABRICO_BE_URL", "https://omniplus-api.techgenzi.com")
AMNONOVENS_BE_URL = os.getenv("AMNONOVENS_BE_URL", "https://omniplus-api.techgenzi.com")
DEFAULT_TOKEN = os.getenv("FABRICO_SERVICE_TOKEN", "")
FABRICO_USERNAME = os.getenv("FABRICO_USERNAME", "rajkumar")
FABRICO_PASSWORD = os.getenv("FABRICO_PASSWORD", "techgenzi password 2026")

_cached_token: Optional[str] = None

def get_auth_token(token: Optional[str] = None) -> str:
    global _cached_token
    if token and token.strip():
        return token.strip()
    if DEFAULT_TOKEN and DEFAULT_TOKEN.strip():
        return DEFAULT_TOKEN.strip()
    if _cached_token and _cached_token.strip():
        return _cached_token.strip()

    # Automatically log in using provided username/password credentials
    if FABRICO_USERNAME and FABRICO_PASSWORD:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{FABRICO_BE_URL}/users/login",
                    json={"username": FABRICO_USERNAME, "password": FABRICO_PASSWORD}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    _cached_token = data.get("access_token", "")
                    return _cached_token or ""
        except Exception:
            pass

    return ""

def get_headers(token: Optional[str] = None, comp_code: Optional[str] = None, tenant_id: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    auth_token = get_auth_token(token)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if comp_code:
        headers["X-Company-Code"] = str(comp_code)
    if tenant_id:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers

async def fetch_get(url: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None) -> Dict[str, Any]:
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers(token), params=clean_params, timeout=15.0)
            if response.status_code == 200:
                return response.json()
            return {"success": False, "status_code": response.status_code, "detail": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

async def fetch_post(url: str, payload: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=get_headers(token), json=payload, timeout=20.0)
            if response.status_code in [200, 201]:
                return response.json()
            return {"success": False, "status_code": response.status_code, "detail": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
