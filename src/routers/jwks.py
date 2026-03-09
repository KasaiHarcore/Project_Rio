"""JWKS endpoint for public key distribution.

Exposes ``GET /.well-known/jwks.json`` so external services (and the
OIDC layer) can verify RS256 JWTs without sharing a private key.
"""

import base64
import hashlib
from typing import Any, Dict, List

from fastapi import APIRouter

from infrastructure.security.jwt_config import JWT_ALGORITHM, JWT_VERIFY_KEY

router = APIRouter(tags=["jwks"])


def _int_to_base64url(n: int) -> str:
    """Encode an arbitrary-size integer as Base64url (no padding)."""
    byte_length = (n.bit_length() + 7) // 8
    raw = n.to_bytes(byte_length, byteorder="big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _build_jwk() -> Dict[str, Any]:
    """Build a JWK dict from the current RSA public key."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    pub_numbers = JWT_VERIFY_KEY.public_numbers()

    # kid = SHA-256 of the DER-encoded public key
    der_bytes = JWT_VERIFY_KEY.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    kid = hashlib.sha256(der_bytes).hexdigest()

    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }


@router.get("/.well-known/jwks.json")
async def jwks_endpoint() -> Dict[str, List[Dict[str, Any]]]:
    """Return the JSON Web Key Set for public key verification."""
    if JWT_ALGORITHM == "RS256":
        return {"keys": [_build_jwk()]}
    return {"keys": []}
