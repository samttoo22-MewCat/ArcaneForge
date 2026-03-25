"""V-02: DM ruling HMAC signing and verification."""
import pytest
from server.dm.signer import sign_payload, verify_payload, create_prompt_packet, is_timestamp_valid
import time


class TestHMAC:
    def test_sign_and_verify(self):
        payload = {"action": "kick the barrel", "player": "hero"}
        sig = sign_payload(payload)
        assert verify_payload(payload, sig) is True

    def test_tampered_payload_fails(self):
        payload = {"action": "kick the barrel"}
        sig = sign_payload(payload)
        tampered = {"action": "kick the barrel", "extra": "injected"}
        assert verify_payload(tampered, sig) is False

    def test_different_key_order_same_result(self):
        p1 = {"b": 2, "a": 1}
        p2 = {"a": 1, "b": 2}
        assert sign_payload(p1) == sign_payload(p2)

    def test_wrong_signature_fails(self):
        payload = {"x": 1}
        assert verify_payload(payload, "000000deadbeef") is False

    def test_empty_payload(self):
        sig = sign_payload({})
        assert verify_payload({}, sig) is True

    def test_create_prompt_packet_has_required_fields(self):
        payload = {"action": "test"}
        packet = create_prompt_packet(payload, session_id="sess_001")
        assert "nonce" in packet
        assert "timestamp" in packet
        assert "signature" in packet
        assert "session_id" in packet
        assert "payload" in packet

    def test_packet_signature_verifiable(self):
        payload = {"action": "test"}
        packet = create_prompt_packet(payload, session_id="sess_001")
        assert verify_payload(packet["payload"], packet["signature"]) is True


class TestTimestamp:
    def test_current_timestamp_valid(self):
        assert is_timestamp_valid(time.time()) is True

    def test_old_timestamp_invalid(self):
        old = time.time() - 400  # beyond 300s nonce TTL
        assert is_timestamp_valid(old) is False

    def test_future_timestamp_within_tolerance(self):
        future = time.time() + 20  # within 30s clock skew
        assert is_timestamp_valid(future) is True

    def test_far_future_invalid(self):
        far = time.time() + 100
        assert is_timestamp_valid(far) is False
