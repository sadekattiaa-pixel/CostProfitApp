import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db import db
from app.services.invoice_service import invoice_service
from app.services.settings_service import settings


class InvoiceTransactionTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(__file__).with_name("_transaction_test.db")
        db.connect(self.db_path)
        settings.clear_cache()
        db.execute("INSERT INTO suppliers (code, name) VALUES ('S1', 'Supplier')")
        self.supplier_id = db.query_one("SELECT id FROM suppliers WHERE code='S1'")["id"]
        db.execute(
            "INSERT INTO products (code, name, category, supplier_id) VALUES ('P1', 'Product', 'Batteries', ?)",
            (self.supplier_id,),
        )
        self.product_id = db.query_one("SELECT id FROM products WHERE code='P1'")["id"]
        db._conn.commit()

    def tearDown(self):
        db.close()
        settings.clear_cache()
        for path in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if path.exists():
                path.unlink()

    def test_failed_line_insert_rolls_back_whole_invoice(self):
        original_execute = db.execute

        def fail_on_items(sql, params=()):
            if "INSERT INTO invoice_items" in sql:
                raise sqlite3.IntegrityError("simulated failure")
            return original_execute(sql, params)

        with patch.object(db, "execute", side_effect=fail_on_items):
            with self.assertRaises(sqlite3.IntegrityError):
                invoice_service.save_draft(
                    None, self.supplier_id, "", "2026-09-27",
                    [{"product_id": self.product_id, "quantity": 1, "purchase_usd": 10, "sale_dzd": 20}],
                    [{"label": "Payment", "amount": 10}], [], [],
                )

        self.assertEqual(db.query_one("SELECT COUNT(*) AS c FROM invoices")["c"], 0)


if __name__ == "__main__":
    unittest.main()
