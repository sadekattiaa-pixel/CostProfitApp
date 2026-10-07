import unittest

from app.services.invoice_calc import (
    CalculationError,
    InvoiceItemInput,
    calculate_invoice,
)


class InvoiceCalculationPrecisionTests(unittest.TestCase):
    def test_decimal_values_are_rounded_for_money(self):
        result = calculate_invoice(
            [InvoiceItemInput(1, 3, 0.1, 1.0)],
            [0.3],
            [],
            [],
        )
        self.assertEqual(result.total_usd, 0.3)
        self.assertEqual(result.net_cost, 0.3)
        self.assertEqual(result.exchange_rate, 1.0)
        self.assertEqual(result.items[0].total_profit, 2.7)

    def test_non_finite_and_negative_values_are_rejected(self):
        valid_item = [InvoiceItemInput(1, 1, 1, 2)]
        for invalid in (float("nan"), float("inf"), -1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CalculationError):
                    calculate_invoice(valid_item, [invalid], [], [])


if __name__ == "__main__":
    unittest.main()
