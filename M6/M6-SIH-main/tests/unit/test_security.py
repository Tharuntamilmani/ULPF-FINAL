"""Unit tests for security utilities."""

from __future__ import annotations

import pytest
from jose import JWTError

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        hashed = hash_password("secret")
        assert hashed != "secret"

    def test_verify_correct_password(self):
        hashed = hash_password("correct-horse")
        assert verify_password("correct-horse", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-horse")
        assert verify_password("wrong-password", hashed) is False

    def test_two_hashes_differ(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123", extra_claims={"roles": ["ADMINISTRATOR"]})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["roles"] == ["ADMINISTRATOR"]

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("not.a.token")

    def test_tampered_token_raises(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_token_type_claim(self):
        token = create_access_token("user-abc")
        payload = decode_access_token(token)
        assert payload["type"] == "access"
