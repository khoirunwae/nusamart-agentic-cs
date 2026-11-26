-- Jalankan seluruh skrip ini di Supabase -> SQL Editor -> New Query

-- 1. Tabel Customers
CREATE TABLE IF NOT EXISTS customers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  default_address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tabel Products
CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price BIGINT NOT NULL,
  stock INT NOT NULL CHECK (stock >= 0),
  description TEXT
);

-- 3. Tabel Orders
CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  customer_email TEXT NOT NULL REFERENCES customers(email),
  product_id TEXT NOT NULL REFERENCES products(id),
  qty INT NOT NULL CHECK (qty > 0),
  total_amount BIGINT NOT NULL,
  shipping_address TEXT NOT NULL,
  payment_method TEXT DEFAULT 'QRIS',
  status TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
  sla_exceeded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Tabel OTP Codes
CREATE TABLE IF NOT EXISTS otp_codes (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Tabel Support & Approval Tickets
CREATE TABLE IF NOT EXISTS tickets (
  ticket_id TEXT PRIMARY KEY,
  order_id TEXT,
  customer_email TEXT,
  ticket_type TEXT NOT NULL, -- 'HUMAN_APPROVAL', 'SLA_ESCALATION', 'PAYMENT_ISSUE', 'GENERAL'
  reason TEXT NOT NULL,
  amount BIGINT DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED', 'RESOLVED'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Tabel Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT,
  event_type TEXT NOT NULL,
  detail TEXT NOT NULL,
  severity TEXT DEFAULT 'INFO',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Fungsi Transaksi Atomik untuk Order Baru + Kurangi Stok
CREATE OR REPLACE FUNCTION place_order_atomic(
  p_name TEXT,
  p_email TEXT,
  p_address TEXT,
  p_product_id TEXT,
  p_qty INT,
  p_payment_method TEXT DEFAULT 'QRIS'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_price BIGINT;
  v_stock INT;
  v_total BIGINT;
  v_order_id TEXT;
BEGIN
  -- Upsert customer
  INSERT INTO customers (name, email, default_address)
  VALUES (p_name, LOWER(TRIM(p_email)), p_address)
  ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    default_address = EXCLUDED.default_address;

  -- Lock baris produk & cek stok
  SELECT price, stock INTO v_price, v_stock
  FROM products
  WHERE id = p_product_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'error', 'Produk tidak ditemukan.');
  END IF;

  IF v_stock < p_qty THEN
    RETURN jsonb_build_object('ok', false, 'error', 'Stok tidak mencukupi. Sisa stok: ' || v_stock);
  END IF;

  -- Kurangi stok
  UPDATE products SET stock = stock - p_qty WHERE id = p_product_id;

  -- Buat Order ID unik
  v_total := v_price * p_qty;
  v_order_id := 'INV-' || LPAD((FLOOR(RANDOM() * 9000 + 1000))::INT::TEXT, 4, '0');

  INSERT INTO orders (order_id, customer_email, product_id, qty, total_amount, shipping_address, payment_method, status)
  VALUES (v_order_id, LOWER(TRIM(p_email)), p_product_id, p_qty, v_total, p_address, p_payment_method, 'PENDING_PAYMENT');

  RETURN jsonb_build_object(
    'ok', true,
    'order_id', v_order_id,
    'total_amount', v_total,
    'remaining_stock', v_stock - p_qty,
    'status', 'PENDING_PAYMENT'
  );
END;
$$;

-- 8. Seed Data Awal (Produk & Contoh Order)
INSERT INTO products (id, name, category, price, stock, description) VALUES
  ('PRD-01', 'Headphone Wireless ANC', 'Elektronik', 420000, 15, 'Headphone Bluetooth dengan Active Noise Cancelling, baterai 30 jam.'),
  ('PRD-02', 'Keyboard Mekanikal TKL', 'Aksesoris PC', 350000, 12, 'Keyboard mekanikal 87 tombol switch tactile, koneksi USB-C.'),
  ('PRD-03', 'Mouse Ergonomis Pro', 'Aksesoris PC', 215000, 20, 'Mouse wireless ergonomis 4000 DPI, silent click.'),
  ('PRD-04', 'Monitor IPS 24 Inch', 'Elektronik', 1250000, 6, 'Monitor Full HD 100Hz panel IPS untuk kerja dan desain.'),
  ('PRD-05', 'SSD NVMe 1TB Gen4', 'Penyimpanan', 890000, 10, 'SSD kecepatan baca hingga 5000 MB/s, garansi resmi 3 tahun.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO customers (name, email, default_address) VALUES
  ('Budi Santoso', 'budi.demo@example.com', 'Jl. Pluit Karang No. 8, Jakarta Utara'),
  ('Siti Aminah', 'siti.demo@example.com', 'Jl. Darmo Permai No. 45, Surabaya')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (order_id, customer_email, product_id, qty, total_amount, shipping_address, payment_method, status, sla_exceeded) VALUES
  ('INV-2048', 'budi.demo@example.com', 'PRD-01', 1, 420000, 'Jl. Pluit Karang No. 8, Jakarta Utara', 'QRIS', 'IN_TRANSIT', TRUE),
  ('INV-3091', 'siti.demo@example.com', 'PRD-02', 1, 350000, 'Jl. Darmo Permai No. 45, Surabaya', 'VA BCA', 'PAID_UNSHIPPED', FALSE),
  ('INV-5521', 'budi.demo@example.com', 'PRD-04', 1, 1250000, 'Jl. Pluit Karang No. 8, Jakarta Utara', 'Kartu Kredit', 'DELIVERED', FALSE)
ON CONFLICT (order_id) DO NOTHING;
