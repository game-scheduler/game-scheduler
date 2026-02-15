# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Discord webhook signature validation dependency.

Provides Ed25519 signature validation for Discord webhook events.
"""

import os

from fastapi import Header, HTTPException, Request
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


async def validate_discord_webhook(
    request: Request,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...),
) -> bytes:
    """
    Validate Discord webhook Ed25519 signature.

    Discord signs webhook payloads using Ed25519 cryptography. This dependency
    validates the signature before allowing the webhook to be processed.

    Signature verification process:
    1. Concatenate timestamp string + raw body bytes
    2. Verify signature against this message using public key
    3. Return validated body if signature is valid

    Args:
        request: FastAPI request object containing webhook payload
        x_signature_ed25519: Discord signature from X-Signature-Ed25519 header
        x_signature_timestamp: Discord timestamp from X-Signature-Timestamp header

    Returns:
        Validated request body as bytes

    Raises:
        HTTPException: 500 if DISCORD_PUBLIC_KEY is not configured
        HTTPException: 401 if signature validation fails
    """
    public_key_hex = os.getenv("DISCORD_PUBLIC_KEY", "")
    if not public_key_hex:
        raise HTTPException(status_code=500, detail="Discord public key not configured")

    body = await request.body()

    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))

        message = x_signature_timestamp.encode() + body
        signature_bytes = bytes.fromhex(x_signature_ed25519)

        verify_key.verify(message, signature_bytes)

        return body
    except (ValueError, BadSignatureError):
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from None
