"""Sends the report e-mail through Gmail SMTP (STARTTLS) with an App Password from backend/.env.
Stdlib only. Never logs the message content (it contains personal data)."""

import smtplib
import ssl
from email.message import EmailMessage

from app.config import Settings


class MailNotConfigured(RuntimeError):
    pass


class MailFailed(RuntimeError):
    pass


def send_email(msg: EmailMessage, settings: Settings) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        raise MailNotConfigured("SMTP_USER / SMTP_PASSWORD missing in backend/.env")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise MailFailed("Gmail a refuzat autentificarea (verificați App Password-ul).") from e
    except (smtplib.SMTPException, OSError) as e:
        raise MailFailed("Serverul de e-mail nu a putut fi contactat.") from e
