
import logging
import os
import smtplib

from email.message import EmailMessage


logger = logging.getLogger(__name__)


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv(
    "SMTP_FROM_NAME",
    "Lasata Support Team",
)


def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> bool:
    """Send a plain-text email using Gmail SMTP."""

    if not all([
        SMTP_USERNAME,
        SMTP_PASSWORD,
        SMTP_FROM_EMAIL,
    ]):
        logger.error("SMTP configuration is incomplete.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)

        logger.info("Email sent successfully to %s", recipient)
        return True

    except Exception:
        logger.exception("Failed to send email to %s", recipient)
        return False


def send_ticket_confirmation_email(
    recipient: str,
    customer_name: str | None,
    ticket_id: int,
    subject: str,
) -> bool:
    """Notify the customer that their support ticket was received."""

    name = customer_name or "Customer"

    email_body = f"""
Dear {name},

Thank you for contacting Lasata Department Store.

We have successfully received your support request and our team is
currently reviewing it.

Ticket Details:
Ticket ID: #{ticket_id}
Subject: {subject}
Status: Under Review

We will notify you by email when an update or decision has been made.

Thank you for your patience and for choosing Lasata.

Regards,
Lasata Support Team
"""

    return send_email(
        recipient=recipient,
        subject=f"Support Ticket Received - #{ticket_id}",
        body=email_body.strip(),
    )


def send_ticket_decision_email(
    recipient: str,
    customer_name: str | None,
    ticket_id: int,
    subject: str,
    decision: str,
) -> bool:
    """Notify the customer when a decision is made on their ticket."""

    name = customer_name or "Customer"

    email_body = f"""
Dear {name},

Our team has reviewed your support request.

Ticket Details:
Ticket ID: #{ticket_id}
Subject: {subject}

Decision / Update:
{decision}

Thank you for choosing Lasata Department Store.

Regards,
Lasata Support Team
"""

    return send_email(
        recipient=recipient,
        subject=f"Support Ticket Update - #{ticket_id}",
        body=email_body.strip(),
    )
