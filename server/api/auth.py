"""OpenRouter OAuth exchange proxy + client-side debug log relay."""
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["auth"])


class DebugLogRequest(BaseModel):
    level: str = "debug"
    message: str


@router.post("/debug/log")
async def debug_log(body: DebugLogRequest):
    print(f"[client:{body.level}] {body.message}")
    return {"ok": True}

OPENROUTER_EXCHANGE_URL = "https://openrouter.ai/api/v1/auth/keys"


class ExchangeRequest(BaseModel):
    code: str


@router.post("/auth/exchange")
async def exchange_oauth_code(body: ExchangeRequest):
    print(f"[OAuth] exchange: code length={len(body.code)}, code[:8]={body.code[:8]}...")
    print(f"[OAuth] exchange: POST → {OPENROUTER_EXCHANGE_URL}")

    payload = {"code": body.code}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            OPENROUTER_EXCHANGE_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    print(f"[OAuth] exchange: response status={resp.status_code}")
    print(f"[OAuth] exchange: response body={resp.text}")

    return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
