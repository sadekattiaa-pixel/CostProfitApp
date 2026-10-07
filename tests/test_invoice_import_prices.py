import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from app.services.excel_invoice_import import ExcelInvoiceImporter


class InvoiceImportPriceMappingTests(unittest.TestCase):
    def test_import_keeps_purchase_and_sale_prices_separate(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Invoices"
        ws.append([
            "invoice_no",
            "date",
            "supplier",
            "product",
            "qty",
            "purchase_price",
            "sale_price",
            "tax",
            "discount",
            "notes",
        ])
        ws.append(["INV-1001", "2026-09-27", "Supplier A", "Widget", 5, 100, 150, 0, 0, ""])

        temp_dir = Path(tempfile.mkdtemp(prefix="invoice_import_"))
        file_path = temp_dir / "invoice.xlsx"
        wb.save(file_path)
        wb.close()

        report = ExcelInvoiceImporter.import_file(str(file_path))

        self.assertEqual(len(report.rows), 1)
        self.assertEqual(report.rows[0].purchase_price, 100)
        self.assertEqual(report.rows[0].sale_price, 150)


if __name__ == "__main__":
    unittest.main()
