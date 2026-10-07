import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.db import db
from app.services.excel_invoice_import import ImportReport, InvoiceRow, ExcelInvoiceImporter
from app.services.settings_service import settings
from app.services.invoice_service import invoice_service
from app.services.product_service import product_service
from app.services.supplier_service import supplier_service
from app.ui.pages.invoice import InvoicePage


class InvoiceImportUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.db_path = Path(__file__).with_name("_invoice_import_ui.db")
        db.connect(self.db_path)
        settings.clear_cache()

    def tearDown(self):
        db.close()
        settings.clear_cache()
        for path in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if path.exists():
                path.unlink()

    def test_imported_supplier_and_product_are_selected_in_existing_page(self):
        page = InvoicePage(language="ar")
        report = ImportReport(rows=[InvoiceRow(
            invoice_no="SUP-100",
            date="2026-09-27",
            supplier="مورد الاختبار",
            product="صنف الاختبار",
            product_code="TEST-ITEM-1",
            qty=2,
            unit_price=10,
            purchase_price=10,
            sale_price=20,
        )])

        self.assertEqual(ExcelInvoiceImporter.save_report_to_db(report), 1)
        invoice_id = db.query_one("SELECT id FROM invoices")["id"]
        page.load_invoice(invoice_id)

        self.assertEqual(page.supplier_combo.currentText(), "مورد الاختبار")
        self.assertEqual(page._item_rows[0]["product_combo"].currentText(), "TEST-ITEM-1")
        self.assertIsNotNone(page._item_rows[0]["product_combo"].current_product_id())

    def test_template_supplier_is_replaced_by_existing_product_supplier(self):
        supplier_id = supplier_service.create("S-001", "المورد الحقيقي")
        product_id = product_service.create(
            "P-0001", "بطارية 100", "Batteries", supplier_id,
        )
        report = ImportReport(rows=[InvoiceRow(
            invoice_no="SUP-101",
            date="2026-09-27",
            supplier="Supplier Example",
            product="P-0001",
            qty=3,
            unit_price=12,
            purchase_price=12,
            sale_price=20,
        )])

        self.assertEqual(ExcelInvoiceImporter.save_report_to_db(report), 1)
        invoice = db.query_one("SELECT id, supplier_id FROM invoices")
        self.assertEqual(invoice["supplier_id"], supplier_id)
        loaded = invoice_service.get_by_id(invoice["id"])
        self.assertEqual(loaded["supplier_name"], "المورد الحقيقي")
        self.assertEqual(loaded["items"][0]["product_id"], product_id)

    def test_historical_supplier_mismatch_still_displays_product_code(self):
        invoice_supplier = supplier_service.create("S-001", "مورد الفاتورة")
        product_supplier = supplier_service.create("S-002", "مورد الصنف")
        product_id = product_service.create(
            "P-0001", "صنف قديم", "Batteries", product_supplier,
        )
        invoice_id = invoice_service.save_draft(
            None, invoice_supplier, "OLD-1", "2026-09-27",
            [{"product_id": product_id, "quantity": 1, "purchase_usd": 10, "sale_dzd": 20}],
            [{"label": "Payment", "amount": 10}], [], [],
        )

        page = InvoicePage(language="ar")
        page.load_invoice(invoice_id)

        self.assertEqual(page.supplier_combo.currentText(), "مورد الفاتورة")
        self.assertEqual(page._item_rows[0]["product_combo"].currentText(), "P-0001")
        self.assertEqual(page._item_rows[0]["product_combo"].current_product_id(), product_id)

    def test_profit_summary_switches_between_loss_and_profit_colors(self):
        supplier_id = supplier_service.create("S-001", "مورد")
        product_id = product_service.create(
            "P-0001", "صنف", "Batteries", supplier_id,
        )
        page = InvoicePage(language="ar")
        page.current_supplier_id = supplier_id
        page._add_item_row(
            product_id=product_id, qty=1, purchase=10, sale=20,
        )
        page._amount_rows_payments[0].amount_input.setText("100")
        page._recalculate()
        self.assertTrue(page._summary_rows["sum_profit__value"].property("loss"))

        page._item_rows[0]["sale"].setText("200")
        page._recalculate()
        self.assertFalse(page._summary_rows["sum_profit__value"].property("loss"))


if __name__ == "__main__":
    unittest.main()
