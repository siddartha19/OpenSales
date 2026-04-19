"""SendGrid wrapper with mock/real toggle.

Mock mode: returns fake message_id, logs locally (does NOT hit SendGrid at all).
Real mode: sends through SendGrid. Set EMAIL_MODE='real' or pass mode='real'.
"""
from __future__ import annotations

import re
import uuid
from typing import Literal

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ..config import (
    EMAIL_FALLBACK_RECIPIENT,
    EMAIL_MODE,
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
    mode: Literal["mock", "real"] | None = None,
) -> dict:
    """Returns {success, message_id, mode, error?}.

    mode=None means use EMAIL_MODE from env. Always default to mock if SendGrid
    key is missing.
    """
    effective_mode = mode or EMAIL_MODE
    if effective_mode != "real" or not SENDGRID_API_KEY:
        return {
            "success": True,
            "message_id": f"mock-{uuid.uuid4().hex[:12]}",
            "mode": "mock",
            "to_email": to_email,
            "subject": subject,
            "preview": body[:200],
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
            "mode": "real",
            "status_code": resp.status_code,
            "to_email": to_email,
        }
    except Exception as e:
        return {
            "success": False,
            "mode": "real",
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
        mode="mock",
    )
    print(res)
