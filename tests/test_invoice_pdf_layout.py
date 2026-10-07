import unittest

from app.services.export_service import export_service


class InvoicePdfLayoutTests(unittest.TestCase):
    def test_image_column_is_between_layout_and_pallet(self):
        columns = ["product_name", "image", "ah", "layout", "pallet", "quantity"]
        ordered = export_service._order_pdf_invoice_columns(columns)
        self.assertEqual(
            ordered,
            ["product_name", "ah", "layout", "image", "pallet", "quantity"],
        )


if __name__ == "__main__":
    unittest.main()
