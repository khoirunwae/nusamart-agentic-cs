import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import streamlit as st
from supabase import create_client, Client


def _get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.environ.get(key, "").strip()


def get_supabase() -> Client:
    raw_url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not raw_url or not key:
        raise RuntimeError("SUPABASE_URL dan SUPABASE_KEY belum diisi di Streamlit Secrets.")
    if "supabase.com/dashboard" in raw_url:
        raise RuntimeError(
            "SUPABASE_URL salah format (terdeteksi URL dashboard). "
            "Gunakan Project URL dari Project Settings -> Data API (format: https://xxxx.supabase.co)."
        )
    parsed = urlparse(raw_url)
    url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else raw_url.rstrip("/")
    return create_client(url, key)


def log_audit(session_id: str, event_type: str, detail: str, severity: str = "INFO") -> None:
    try:
        sb = get_supabase()
        sb.table("audit_logs").insert({
            "session_id": session_id,
            "event_type": event_type,
            "detail": detail,
            "severity": severity,
        }).execute()
    except Exception:
        pass


def fetch_products() -> list[dict]:
    sb = get_supabase()
    res = sb.table("products").select("*").order("id").execute()
    return res.data or []


def fetch_orders(limit: int = 50) -> list[dict]:
    sb = get_supabase()
    res = sb.table("orders").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def get_order_by_id(order_id: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("orders").select("*").eq("order_id", order_id.upper().strip()).limit(1).execute()
    return res.data[0] if res.data else None


def place_order_atomic(name: str, email: str, address: str, product_id: str, qty: int, payment_method: str = "QRIS") -> dict:
    sb = get_supabase()
    res = sb.rpc("place_order_atomic", {
        "p_name": name,
        "p_email": email,
        "p_address": address,
        "p_product_id": product_id,
        "p_qty": int(qty),
        "p_payment_method": payment_method,
    }).execute()
    return res.data


def update_order_status(order_id: str, new_status: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("orders")
        .update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("order_id", order_id.upper().strip())
        .execute()
    )
    return res.data[0] if res.data else None


def update_order_address(order_id: str, new_address: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("orders")
        .update({"shipping_address": new_address, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("order_id", order_id.upper().strip())
        .execute()
    )
    return res.data[0] if res.data else None


def update_order_payment_method(order_id: str, new_method: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("orders")
        .update({"payment_method": new_method, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("order_id", order_id.upper().strip())
        .execute()
    )
    return res.data[0] if res.data else None


def save_otp(email: str, code: str, ttl_minutes: int = 10) -> None:
    sb = get_supabase()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()
    sb.table("otp_codes").insert({
        "email": email.lower().strip(),
        "code": code,
        "expires_at": expires_at,
        "used": False,
    }).execute()


def verify_otp_db(email: str, code: str) -> bool:
    sb = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    res = (
        sb.table("otp_codes")
        .select("*")
        .eq("email", email.lower().strip())
        .eq("code", code.strip())
        .eq("used", False)
        .gte("expires_at", now_iso)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return False
    otp_row = res.data[0]
    sb.table("otp_codes").update({"used": True}).eq("id", otp_row["id"]).execute()
    return True


def create_ticket(ticket_id: str, order_id: str, email: str, ticket_type: str, reason: str, amount: int = 0) -> dict:
    sb = get_supabase()
    res = sb.table("tickets").insert({
        "ticket_id": ticket_id,
        "order_id": order_id,
        "customer_email": email,
        "ticket_type": ticket_type,
        "reason": reason,
        "amount": amount,
        "status": "PENDING",
    }).execute()
    return res.data[0] if res.data else {}


def fetch_tickets(limit: int = 50) -> list[dict]:
    sb = get_supabase()
    res = sb.table("tickets").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def resolve_ticket(ticket_id: str, decision: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("tickets").update({"status": decision}).eq("ticket_id", ticket_id).execute()
    return res.data[0] if res.data else None


def fetch_audit_logs(limit: int = 50) -> list[dict]:
    sb = get_supabase()
    res = sb.table("audit_logs").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data or []
