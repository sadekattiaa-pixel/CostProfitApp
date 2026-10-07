import unittest
from pathlib import Path

from app.db import db
from app.services.invoice_service import invoice_service
from app.services.reports_service import reports_service
from app.services.settings_service import settings


class ReportsAndArchiveTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(__file__).with_name("_reports_archive_test.db")
        db.connect(self.db_path)
        settings.clear_cache()
        db.execute("INSERT INTO suppliers (code, name) VALUES ('S1', 'Supplier')")
        self.supplier_id = db.query_one("SELECT id FROM suppliers WHERE code='S1'")["id"]
        for code, name in (("P1", "Product One"), ("P2", "Product Two")):
            db.execute(
                "INSERT INTO products (code, name, category, supplier_id) VALUES (?, ?, 'Batteries', ?)",
                (code, name, self.supplier_id),
            )
        self.product_ids = {
            row["code"]: row["id"] for row in db.query_all("SELECT id, code FROM products")
        }
        db._conn.commit()

    def tearDown(self):
        db.close()
        settings.clear_cache()
        for path in (
            self.db_path,
            Path(str(self.db_path) + "-wal"),
            Path(str(self.db_path) + "-shm"),
        ):
            if path.exists():
                path.unlink()

    def _archive(self, product: str, quantity: float, sale_price: float) -> int:
        purchase_price = 10
        return invoice_service.archive(
            None,
            self.supplier_id,
            f"SUP-{product}",
            "2026-09-29",
            [{
                "product_id": self.product_ids[product],
                "quantity": quantity,
                "purchase_usd": purchase_price,
                "sale_dzd": sale_price,
            }],
            [{"label": "Payment", "amount": quantity * purchase_price}],
            [],
            [],
        )

    def test_archiving_updates_status_and_report_totals(self):
        invoice_id = self._archive("P1", 2, 15)

        invoice = invoice_service.get_by_id(invoice_id)
        self.assertEqual(invoice["status"], "archived")
        self.assertIsNotNone(invoice["archived_at"])

        report = reports_service.profit_report(period="all")
        self.assertEqual(report["stats"]["invoices_count"], 1)
        self.assertEqual(report["stats"]["total_sales"], 30)
        self.assertEqual(report["stats"]["total_profit"], 10)

    def test_profit_and_sales_rankings_respect_top_n(self):
        self._archive("P1", 2, 20)
        self._archive("P2", 5, 12)

        profitable = reports_service.most_profitable_report(period="all", top_n=1)
        selling = reports_service.best_selling_report(period="all", top_n=1)

        self.assertEqual(len(profitable["products"]), 1)
        self.assertEqual(profitable["products"][0]["code"], "P1")
        self.assertEqual(selling["products"][0]["code"], "P2")

    def test_deleting_invoice_cascades_to_lines(self):
        invoice_id = self._archive("P1", 1, 15)
        invoice_service.delete(invoice_id)

        self.assertIsNone(invoice_service.get_by_id(invoice_id))
        count = db.query_one(
            "SELECT COUNT(*) AS count FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,),
        )["count"]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
