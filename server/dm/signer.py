"""HMAC-SHA256 signing and verification for DM prompt packets."""
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from server.config import settings


def sign_payload(payload: dict) -> str:
    """Return HMAC-SHA256 hex digest for the given payload dict."""
    message = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(settings.hmac_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_payload(payload: dict, signature: str) -> bool:
    """Constant-time HMAC verification."""
    expected = sign_payload(payload)
    return hmac.compare_digest(expected, signature)


def create_prompt_packet(payload: dict, session_id: str) -> dict:
    """Build a signed packet to send to the client."""
    nonce = secrets.token_hex(16)
    timestamp = time.time()
    full_payload = {**payload, "nonce": nonce, "timestamp": timestamp, "session_id": session_id}
    signature = sign_payload(full_payload)
    return {
        "payload": full_payload,
        "nonce": nonce,
        "timestamp": timestamp,
        "session_id": session_id,
        "signature": signature,
    }


def is_timestamp_valid(timestamp: float, ttl_seconds: int = None) -> bool:
    ttl = ttl_seconds or settings.nonce_ttl_seconds
    now = time.time()
    return (now - ttl) <= timestamp <= (now + 30)
