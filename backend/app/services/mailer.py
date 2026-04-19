"""SendGrid wrapper. Real sends only — no mock mode."""
from __future__ import annotations

import os
import re
import uuid

# Ensure Python's stdlib SSL has a usable CA bundle BEFORE importing sendgrid.
# On some macOS Python builds, ssl.get_default_verify_paths() points at
# /usr/local/mysql/ssl/cert.pem (or similar) which fails to verify SendGrid's
# TLS chain ("self signed certificate in certificate chain"). Pointing at
# certifi's bundle fixes this without requiring any shell env setup.
try:
    import certifi as _certifi

    _ca = _certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _ca)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
except ImportError:  # certifi missing — leave env untouched, surface real error
    pass

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..config import (
    EMAIL_FALLBACK_RECIPIENT,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_FROM_NAME,
)


def derive_email_for_demo(first_name: str, company_domain: str | None) -> str:
    """Plan: prospects firstname@<company_domain>.com,
    fallback to demo@salesos.opensource.

    Used when AE has a name + company but no verified email.
    """
    if not first_name:
        return EMAIL_FALLBACK_RECIPIENT
    fn = re.sub(r"[^a-z]", "", first_name.lower().split()[0])
    if not fn:
        return EMAIL_FALLBACK_RECIPIENT
    if company_domain and "." in company_domain:
        return f"{fn}@{company_domain.lstrip('www.').strip()}"
    return EMAIL_FALLBACK_RECIPIENT


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> dict:
    """Send an email via SendGrid. Returns {success, message_id, error?}."""
    if not SENDGRID_API_KEY:
        return {
            "success": False,
            "error": "SENDGRID_API_KEY is not configured",
            "to_email": to_email,
        }

    try:
        msg = Mail(
            from_email=(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
            to_emails=to_email,
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(msg)
        msg_id = resp.headers.get("X-Message-Id", "") if hasattr(resp, "headers") else ""
        return {
            "success": 200 <= resp.status_code < 300,
            "message_id": msg_id or f"sg-{uuid.uuid4().hex[:12]}",
            "status_code": resp.status_code,
            "to_email": to_email,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "to_email": to_email,
        }


if __name__ == "__main__":
    print(derive_email_for_demo("Riya", "velocity.ai"))
    print(derive_email_for_demo("", None))
    res = send_email(
        to_email="demo@salesos.opensource",
        to_name="Demo",
        subject="Test from SalesOS",
        body="Hello from the SalesOS backend smoke test.",
    )
    print(res)
