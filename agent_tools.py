import random
import streamlit as st
import db
import rag_kb
from email_otp import send_otp_email


def _session_id() -> str:
    return st.session_state.get("session_id", "anon-session")


def _verified_email() -> str | None:
    return st.session_state.get("verified_email")


def search_sop_rag(query: str) -> dict:
    """Mencari dokumen SOP resmi toko (pengiriman, retur, pembatalan, pembayaran) via RAG."""
    docs = rag_kb.search_sop(query)
    db.log_audit(_session_id(), "TOOL_RAG_SEARCH", f"query={query}")
    return {"documents": docs}


def list_products() -> dict:
    """Mengambil daftar katalog produk beserta harga dan stok real-time dari database."""
    products = db.fetch_products()
    db.log_audit(_session_id(), "TOOL_LIST_PRODUCTS", f"count={len(products)}")
    return {"products": products}


def place_new_order(
    customer_name: str,
    customer_email: str,
    shipping_address: str,
    product_id: str,
    qty: int = 1,
    payment_method: str = "QRIS",
) -> dict:
    """Membuat pesanan baru untuk customer baru/lama dan langsung mengurangi stok produk secara atomik di database."""
    result = db.place_order_atomic(
        name=customer_name,
        email=customer_email,
        address=shipping_address,
        product_id=product_id.upper().strip(),
        qty=qty,
        payment_method=payment_method,
    )
    db.log_audit(_session_id(), "TOOL_PLACE_ORDER", f"email={customer_email}, product={product_id}, result={result}")
    return result


def request_email_otp(email: str) -> dict:
    """Mengirim kode OTP 6 digit ke email customer untuk memverifikasi kepemilikan akun sebelum akses data order sensitif."""
    code = f"{random.randint(100000, 999999)}"
    clean_email = email.lower().strip()
    db.save_otp(clean_email, code)
    send_res = send_otp_email(clean_email, code)
    db.log_audit(_session_id(), "TOOL_REQUEST_OTP", f"email={clean_email}, mode={send_res.get('mode')}")
    return {
        "ok": True,
        "email": clean_email,
        "delivery_mode": send_res.get("mode"),
        "info": send_res.get("message"),
    }


def verify_email_otp(email: str, otp_code: str) -> dict:
    """Memverifikasi kode OTP 6 digit yang dimasukkan customer."""
    clean_email = email.lower().strip()
    valid = db.verify_otp_db(clean_email, otp_code)
    if valid:
        st.session_state["verified_email"] = clean_email
        db.log_audit(_session_id(), "AUTH_OTP_SUCCESS", f"email={clean_email}")
        return {"verified": True, "email": clean_email, "message": "Verifikasi OTP berhasil."}
    db.log_audit(_session_id(), "AUTH_OTP_FAILED", f"email={clean_email}", severity="WARNING")
    return {"verified": False, "message": "Kode OTP salah atau sudah kedaluwarsa."}


def _check_order_access(order_id: str) -> tuple[dict | None, dict | None]:
    v_email = _verified_email()
    if not v_email:
        return None, {
            "ok": False,
            "requires_otp": True,
            "message": "Akses ditolak: Customer wajib verifikasi Email OTP terlebih dahulu sebelum melihat atau mengubah pesanan.",
        }
    order = db.get_order_by_id(order_id)
    if not order:
        return None, {"ok": False, "message": f"Pesanan {order_id} tidak ditemukan."}
    if order["customer_email"].lower() != v_email.lower():
        db.log_audit(_session_id(), "AUTH_MISMATCH", f"verified={v_email} tried order={order_id}", severity="WARNING")
        return None, {"ok": False, "message": "Pesanan ini tidak terdaftar pada email yang Anda verifikasi."}
    return order, None


def track_order(order_id: str) -> dict:
    """Melacak status pesanan dari database. Memerlukan verifikasi Email OTP terlebih dahulu."""
    order, err = _check_order_access(order_id)
    if err:
        return err
    extra_ticket = None
    if order.get("sla_exceeded") and order["status"] == "IN_TRANSIT":
        tck = f"TCK-{random.randint(1000, 9999)}"
        db.create_ticket(tck, order["order_id"], order["customer_email"], "SLA_ESCALATION", "Pengiriman melewati batas SLA kurir")
        extra_ticket = tck
    db.log_audit(_session_id(), "TOOL_TRACK_ORDER", f"order_id={order['order_id']}, status={order['status']}")
    return {"ok": True, "order": order, "auto_priority_ticket": extra_ticket}


def confirm_delivery(order_id: str, confirmed_by_customer: bool = False) -> dict:
    """Mengubah status pesanan IN_TRANSIT menjadi DELIVERED setelah customer mengonfirmasi barang sudah sampai."""
    order, err = _check_order_access(order_id)
    if err:
        return err
    if not confirmed_by_customer:
        return {"ok": False, "needs_confirmation": True, "message": "Minta konfirmasi eksplisit customer sebelum mengubah status menjadi DELIVERED."}
    if order["status"] != "IN_TRANSIT":
        return {"ok": False, "message": f"Status pesanan saat ini {order['status']}, bukan IN_TRANSIT."}
    updated = db.update_order_status(order_id, "DELIVERED")
    db.log_audit(_session_id(), "TOOL_CONFIRM_DELIVERY", f"order_id={order_id} -> DELIVERED")
    return {"ok": True, "order": updated}


def cancel_order(order_id: str, confirmed_by_customer: bool = False) -> dict:
    """Membatalkan pesanan jika status masih PENDING_PAYMENT atau PAID_UNSHIPPED dan sudah dikonfirmasi customer."""
    order, err = _check_order_access(order_id)
    if err:
        return err
    if order["status"] not in ("PENDING_PAYMENT", "PAID_UNSHIPPED"):
        return {"ok": False, "message": f"Pesanan berstatus {order['status']} sudah tidak dapat dibatalkan."}
    if not confirmed_by_customer:
        return {"ok": False, "needs_confirmation": True, "message": "Minta konfirmasi eksplisit customer (misal: YA) sebelum membatalkan."}
    updated = db.update_order_status(order_id, "CANCELLED")
    db.log_audit(_session_id(), "TOOL_CANCEL_ORDER", f"order_id={order_id} -> CANCELLED")
    return {"ok": True, "order": updated}


def change_shipping_address(order_id: str, new_address: str, confirmed_by_customer: bool = False) -> dict:
    """Mengubah alamat pengiriman jika pesanan belum dikirim (PENDING_PAYMENT atau PAID_UNSHIPPED)."""
    order, err = _check_order_access(order_id)
    if err:
        return err
    if order["status"] not in ("PENDING_PAYMENT", "PAID_UNSHIPPED"):
        return {"ok": False, "message": f"Alamat tidak dapat diubah karena status pesanan sudah {order['status']}."}
    if not confirmed_by_customer:
        return {"ok": False, "needs_confirmation": True, "message": f"Minta konfirmasi eksplisit customer untuk ubah alamat ke: {new_address}"}
    updated = db.update_order_address(order_id, new_address)
    db.log_audit(_session_id(), "TOOL_CHANGE_ADDRESS", f"order_id={order_id} -> {new_address}")
    return {"ok": True, "order": updated}


def request_refund(order_id: str, reason: str) -> dict:
    """Memproses pengajuan refund. Nominal <= Rp 500.000 otomatis; > Rp 500.000 wajib Human Approval staf."""
    order, err = _check_order_access(order_id)
    if err:
        return err
    amount = int(order["total_amount"])
    if amount > 500000:
        apr_id = f"APR-{random.randint(100, 999)}"
        db.create_ticket(apr_id, order["order_id"], order["customer_email"], "HUMAN_APPROVAL", reason, amount)
        db.log_audit(_session_id(), "HITL_APPROVAL_CREATED", f"ticket={apr_id}, order={order_id}, amount={amount}", severity="WARNING")
        return {
            "ok": True,
            "requires_human_approval": True,
            "ticket_id": apr_id,
            "amount": amount,
            "message": f"Nominal Rp {amount:,} melebihi batas otomatis (Rp 500.000). Tiket {apr_id} diteruskan ke antrean persetujuan staf.",
        }
    updated = db.update_order_status(order_id, "REFUNDED")
    db.log_audit(_session_id(), "TOOL_AUTO_REFUND", f"order={order_id}, amount={amount}")
    return {"ok": True, "requires_human_approval": False, "order": updated, "amount": amount}


def create_support_ticket(order_id: str, issue_summary: str, ticket_type: str = "PAYMENT_ISSUE") -> dict:
    """Membuat tiket layanan pelanggan untuk kendala pembayaran atau eskalasi ke staf manusia."""
    v_email = _verified_email() or "guest@unknown"
    tck = f"TCK-{random.randint(1000, 9999)}"
    ticket = db.create_ticket(tck, order_id.upper().strip(), v_email, ticket_type, issue_summary, 0)
    db.log_audit(_session_id(), "TOOL_CREATE_TICKET", f"ticket={tck}, order={order_id}, type={ticket_type}")
    return {"ok": True, "ticket": ticket}


ALL_TOOLS = [
    search_sop_rag,
    list_products,
    place_new_order,
    request_email_otp,
    verify_email_otp,
    track_order,
    confirm_delivery,
    cancel_order,
    change_shipping_address,
    request_refund,
    create_support_ticket,
]

TOOL_MAP = {fn.__name__: fn for fn in ALL_TOOLS}
