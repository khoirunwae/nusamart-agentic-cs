import os
import smtplib
from email.message import EmailMessage
import streamlit as st


def _get_secret(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.environ.get(key, default).strip()


def send_otp_email(recipient_email: str, otp_code: str) -> dict:
    """Mengirim kode OTP 6 digit ke email customer melalui Gmail SMTP."""
    smtp_user = _get_secret("SMTP_USER")
    smtp_pass = _get_secret("SMTP_APP_PASSWORD")

    if not smtp_user or not smtp_pass:
        return {
            "sent": False,
            "mode": "DEMO_FALLBACK",
            "message": (
                "SMTP_USER / SMTP_APP_PASSWORD belum dikonfigurasi di Secrets. "
                f"Untuk pengujian demo lokal, gunakan kode OTP: {otp_code}"
            ),
        }

    msg = EmailMessage()
    msg["Subject"] = f"Kode Verifikasi OTP NusaMart: {otp_code}"
    msg["From"] = f"NusaMart Customer Service <{smtp_user}>"
    msg["To"] = recipient_email
    msg.set_content(
        f"Halo,\n\n"
        f"Kode verifikasi OTP Anda untuk layanan NusaMart Customer Service adalah:\n\n"
        f"    {otp_code}\n\n"
        f"Kode ini berlaku selama 10 menit. Jangan bagikan kode ini kepada siapa pun.\n\n"
        f"Salam,\nNusaMart Support Team"
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"sent": True, "mode": "GMAIL_SMTP", "message": f"OTP berhasil dikirim ke {recipient_email}."}
    except Exception as exc:
        return {"sent": False, "mode": "SMTP_ERROR", "message": f"Gagal mengirim email OTP: {exc}"}
