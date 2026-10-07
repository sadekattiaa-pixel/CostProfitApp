PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    address     TEXT,
    email       TEXT,
    phone       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_suppliers_code ON suppliers(code);

CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    category      TEXT NOT NULL,
    pattern       TEXT,
    ah            REAL,
    l             REAL,
    w             REAL,
    h             REAL,
    oh            REAL,
    layout        INTEGER,
    layout_image  TEXT,
    pallet        INTEGER,
    supplier_id   INTEGER NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_products_code     ON products(code);
CREATE INDEX IF NOT EXISTS idx_products_name     ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id);

DROP TRIGGER IF EXISTS trg_products_unique_name_insert;
CREATE TRIGGER IF NOT EXISTS trg_products_unique_name_insert
BEFORE INSERT ON products
WHEN NEW.category = 'Batteries' AND EXISTS (
    SELECT 1 FROM products
    WHERE category = 'Batteries' AND TRIM(name) COLLATE NOCASE = TRIM(NEW.name) COLLATE NOCASE
)
BEGIN
    SELECT RAISE(ABORT, 'Product name already exists.');
END;

DROP TRIGGER IF EXISTS trg_products_unique_name_update;
CREATE TRIGGER IF NOT EXISTS trg_products_unique_name_update
BEFORE UPDATE OF name ON products
WHEN NEW.category = 'Batteries' AND EXISTS (
    SELECT 1 FROM products
    WHERE category = 'Batteries' AND id != OLD.id
      AND TRIM(name) COLLATE NOCASE = TRIM(NEW.name) COLLATE NOCASE
)
BEGIN
    SELECT RAISE(ABORT, 'Product name already exists.');
END;

CREATE TABLE IF NOT EXISTS invoices (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no          TEXT UNIQUE NOT NULL,
    supplier_invoice_no TEXT,
    supplier_id         INTEGER NOT NULL,
    invoice_date        TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    total_payments      REAL DEFAULT 0,
    total_discounts     REAL DEFAULT 0,
    net_payments        REAL DEFAULT 0,
    total_expenses      REAL DEFAULT 0,
    net_cost            REAL DEFAULT 0,
    total_usd           REAL DEFAULT 0,
    exchange_rate       REAL DEFAULT 0,
    total_sales         REAL DEFAULT 0,
    total_profit        REAL DEFAULT 0,
    profit_margin       REAL DEFAULT 0,
    display_fields      TEXT,
    notes               TEXT,
    notes2              TEXT,
    archived_snapshot   TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT,
    archived_at         TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_invoices_no       ON invoices(invoice_no);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date     ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_status   ON invoices(status);

CREATE TABLE IF NOT EXISTS invoice_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id        INTEGER NOT NULL,
    product_id        INTEGER NOT NULL,
    line_no           INTEGER NOT NULL,
    quantity          REAL NOT NULL,
    pallet            INTEGER,
    purchase_usd      REAL NOT NULL,
    purchase_dzd      REAL NOT NULL,
    sale_dzd          REAL NOT NULL,
    total_usd         REAL NOT NULL,
    total_dzd         REAL NOT NULL,
    total_sale        REAL NOT NULL,
    unit_profit       REAL NOT NULL,
    total_profit      REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_items_invoice ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON invoice_items(product_id);

CREATE TABLE IF NOT EXISTS invoice_payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id  INTEGER NOT NULL,
    label       TEXT,
    amount      REAL NOT NULL,
    line_no     INTEGER NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payments_invoice ON invoice_payments(invoice_id);

CREATE TABLE IF NOT EXISTS invoice_discounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id  INTEGER NOT NULL,
    label       TEXT,
    amount      REAL NOT NULL,
    line_no     INTEGER NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_discounts_invoice ON invoice_discounts(invoice_id);

CREATE TABLE IF NOT EXISTS invoice_expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id  INTEGER NOT NULL,
    label       TEXT NOT NULL,
    amount      REAL NOT NULL,
    line_no     INTEGER NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_invoice ON invoice_expenses(invoice_id);

CREATE TABLE IF NOT EXISTS expense_templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    label      TEXT UNIQUE NOT NULL,
    is_default INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    message    TEXT,
    machine    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_event_created ON event_log(created_at);
CREATE TABLE IF NOT EXISTS layout_images (
    filename TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
