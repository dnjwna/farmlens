"""
Delivery of password-reset codes. One function, swappable providers:

- console: development only. The code is written to the server log.
- openwa:  self-hosted OpenWA gateway (https://github.com/rmyndharis/OpenWA).
           Unofficial WhatsApp client: the sending number can be restricted or banned,
           and first messages to new contacts may not arrive. Use a dedicated number,
           and move to the official WhatsApp Cloud API or an SMS gateway for production.

To add a provider, add a branch in send_reset_code(); callers do not change.
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OTPDeliveryError(Exception):
    pass


def to_whatsapp_chat_id(canonical_phone: str) -> str:
    """canonical_phone is digits with country code, e.g. 6281234567890."""
    return f"{canonical_phone}@c.us"


def build_message(code: str, ttl_minutes: int) -> str:
    return (
        f"Kode reset password FarmLens: {code}\n"
        f"Berlaku {ttl_minutes} menit.\n\n"
        "Jangan berikan kode ini ke siapa pun, termasuk orang yang mengaku petugas FarmLens."
    )


async def send_reset_code(canonical_phone: str, code: str, ttl_minutes: int) -> None:
    provider = settings.OTP_PROVIDER.lower().strip()
    masked = f"{canonical_phone[:4]}****{canonical_phone[-3:]}"

    if provider == "console":
        logger.warning("[DEV OTP] reset code for %s: %s (OTP_PROVIDER=console, do not use in production)", masked, code)
        return

    if provider == "openwa":
        if not (settings.OPENWA_API_KEY and settings.OPENWA_SESSION_ID):
            raise OTPDeliveryError("OPENWA_API_KEY / OPENWA_SESSION_ID belum diisi")
        url = f"{settings.OPENWA_BASE_URL.rstrip('/')}/sessions/{settings.OPENWA_SESSION_ID}/messages/send-text"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                headers={"X-API-Key": settings.OPENWA_API_KEY},
                json={"chatId": to_whatsapp_chat_id(canonical_phone), "text": build_message(code, ttl_minutes)},
            )
        if response.status_code >= 400:
            raise OTPDeliveryError(f"OpenWA {response.status_code}: {response.text[:200]}")
        logger.info("Reset code sent via OpenWA to %s", masked)
        return

    raise OTPDeliveryError(f"OTP_PROVIDER tidak dikenal: {provider!r}")
