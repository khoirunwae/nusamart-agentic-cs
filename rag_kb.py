import re

SOP_DOCUMENTS = [
    {
        "id": "SOP-01",
        "title": "Kebijakan Pengiriman & SLA Kurir",
        "content": (
            "Estimasi pengiriman reguler Pulau Jawa adalah 2-3 hari kerja dan luar Jawa 4-7 hari kerja. "
            "Jika status pesanan IN_TRANSIT dan melewati batas SLA pengiriman, sistem wajib membuatkan "
            "tiket prioritas eskalasi logistik agar tim kurir segera menindaklanjuti."
        ),
    },
    {
        "id": "SOP-02",
        "title": "Kebijakan Pembatalan & Ubah Alamat",
        "content": (
            "Pembeli hanya dapat membatalkan pesanan atau mengubah alamat pengiriman jika status pesanan "
            "masih PENDING_PAYMENT atau PAID_UNSHIPPED (belum diserahkan ke kurir). Jika status sudah "
            "IN_TRANSIT atau DELIVERED, pembatalan dan perubahan alamat otomatis ditolak."
        ),
    },
    {
        "id": "SOP-03",
        "title": "Kebijakan Retur & Refund",
        "content": (
            "Pengajuan retur atau refund berlaku maksimal 7 hari kalender setelah status DELIVERED untuk "
            "barang rusak atau tidak sesuai. Untuk nominal <= Rp 500.000 dapat diproses otomatis setelah "
            "verifikasi OTP. Untuk nominal > Rp 500.000 wajib melalui persetujuan staf manusia (Human Approval)."
        ),
    },
    {
        "id": "SOP-04",
        "title": "Metode Pembayaran & Kendala Transaksi",
        "content": (
            "NusaMart menerima QRIS, Virtual Account (BCA, Mandiri, BNI), E-Wallet, dan Kartu Kredit. "
            "Jika saldo terpotong namun status masih PENDING_PAYMENT, agen membuatkan tiket rekonsiliasi "
            "keuangan agar tim finance memverifikasi dalam 1x24 jam."
        ),
    },
]


def search_sop(query: str, top_k: int = 2) -> list[dict]:
    """Pencarian dokumen SOP berbasis pencocokan kata kunci (RAG ringan)."""
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for doc in SOP_DOCUMENTS:
        doc_tokens = set(re.findall(r"[a-z0-9]+", (doc["title"] + " " + doc["content"]).lower()))
        score = len(tokens.intersection(doc_tokens))
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [d for s, d in scored[:top_k] if s > 0]
    return results if results else SOP_DOCUMENTS[:top_k]
