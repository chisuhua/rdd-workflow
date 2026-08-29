"""HMAC-SHA256 verification for webhook receiver (acceptance: 4+ exceptions)."""
from __future__ import annotations

import hashlib
import hmac

import pytest

from skills._lib.schedulers.webhook_receiver import verify_signature


class TestHmacVerification:
    """Unit tests for HMAC signature verification (no server needed)."""

    def _sign(self, secret: str, payload: bytes) -> str:
        """Produce a GitHub-style 'sha256=<hex>' signature."""
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_passes(self):
        secret = "s3cret"
        payload = b'{"event":"push"}'
        sig = self._sign(secret, payload)
        assert verify_signature(secret, sig, payload) is True

    def test_invalid_signature_rejected(self):
        secret = "s3cret"
        payload = b'{"event":"push"}'
        wrong = "0" * 64
        assert verify_signature(secret, wrong, payload) is False

    def test_missing_signature_rejected(self):
        secret = "s3cret"
        payload = b'{"event":"push"}'
        assert verify_signature(secret, "", payload) is False

    def test_wrong_secret_rejected(self):
        """A signature produced with a different secret must fail."""
        payload = b'{"event":"push"}'
        good_sig = self._sign("other-secret", payload)
        assert verify_signature("s3cret", good_sig, payload) is False

    def test_tampered_payload_rejected(self):
        """Signature valid for original body must fail for modified body."""
        secret = "s3cret"
        original = b'{"event":"push"}'
        tampered = b'{"event":"delete"}'
        sig = self._sign(secret, original)
        assert verify_signature(secret, sig, tampered) is False
