# NusaMart Agentic AI Customer Service (E-Commerce Demo)

Aplikasi **Agentic AI Customer Service** berbasis **Python + Streamlit + Gemini API (Function Calling) + Supabase (PostgreSQL) + Gmail SMTP (Email OTP)** yang dirancang 100% menggunakan layanan *free tier*.

## Fitur Utama
- **Chatbot Agentic AI (`gemini-2.5-flash`)**: Melakukan *Perceive → Plan → Act → Verify → Respond* dengan pemanggilan *tool* terstruktur.
- **Database Persisten (Supabase)**: Customer baru otomatis tercatat saat memesan (`place_order_atomic`), stok produk langsung berkurang secara atomik, dan status order bisa diperbarui (`PENDING_PAYMENT` → `PAID_UNSHIPPED` → `IN_TRANSIT` → `DELIVERED` / `CANCELLED` / `REFUNDED`).
- **Progressive Verification via Email OTP**: Tanya produk/SOP tanpa login; aksi sensitif (lacak, batal, ubah alamat, refund, konfirmasi terima) wajib verifikasi OTP ke email customer.
- **Human-in-the-Loop & Guardrails**: Refund > Rp 500.000 otomatis ditahan ke tab *Admin & Human Approval*, serta perlindungan terhadap *Prompt Injection* yang tercatat di `audit_logs`.

---

## Panduan Deploy Gratis Online (Langkah Demi Langkah)

### 1. Siapkan Database di Supabase (Gratis)
1. Buka [supabase.com](https://supabase.com) → **Start your project** → buat *New Project* (ingat password database).
2. Di menu kiri, buka **SQL Editor** → **New Query**.
3. Salin seluruh isi file `supabase_schema.sql` dari folder ini, tempel ke editor, lalu klik **Run**.
4. Buka **Project Settings** (ikon gerigi) → **Data API / API** → salin **Project URL** (`SUPABASE_URL`) dan **anon public key** (atau `service_role` key) sebagai `SUPABASE_KEY`.

### 2. Ambil Gemini API Key (Gratis)
1. Buka [aistudio.google.com](https://aistudio.google.com) → login dengan akun Google.
2. Klik **Get API key** → **Create API key** → salin key tersebut sebagai `GEMINI_API_KEY`.

### 3. Siapkan Email Pengirim OTP Toko (Gratis via Gmail)
1. Buat akun Gmail baru khusus toko (misalnya `nusamart.otp@gmail.com`) atau gunakan Gmail yang ada.
2. Aktifkan **2-Step Verification** di [myaccount.google.com/security](https://myaccount.google.com/security).
3. Cari menu **App passwords** → buat App Password baru (pilih *Mail* / *Other*, beri nama `NusaMart OTP`) → salin 16 karakter sandi tersebut sebagai `SMTP_APP_PASSWORD`.

### 4. Upload Kode ke GitHub
1. Buat repositori baru di [github.com](https://github.com) (bisa *Public* atau *Private*).
2. Upload seluruh isi folder `nusamart_agentic_cs` ini ke repositori tersebut (pastikan `.streamlit/secrets.toml` **tidak** ikut ter-upload).

### 5. Deploy Online ke Streamlit Community Cloud (Gratis)
1. Buka [share.streamlit.io](https://share.streamlit.io) → login dengan GitHub.
2. Klik **Create app** → pilih repositori GitHub kamu, branch `main`, dan **Main file path**: `app.py`.
3. Sebelum atau sesudah deploy, klik **Advanced settings** (atau **Settings → Secrets**) lalu isi:
   ```toml
   GEMINI_API_KEY = "isi_gemini_api_key_kamu"
   SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
   SUPABASE_KEY = "isi_supabase_key_kamu"
   SMTP_USER = "nusamart.otp@gmail.com"
   SMTP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   ```
4. Klik **Deploy** — dalam ~1–2 menit aplikasi kamu aktif dengan URL publik `https://namaproject.streamlit.app` siap didemokan ke dosen!
