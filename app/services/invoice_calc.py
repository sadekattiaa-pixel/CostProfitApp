"""
منطق حساب الفاتورة.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class CalculationError(Exception):
    pass


MONEY = Decimal("0.01")
RATE = Decimal("0.000001")
PERCENT = Decimal("0.0001")


def _decimal(value, label: str) -> Decimal:
    """Convert user/database numbers without inheriting binary float error."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise CalculationError(f"{label} must be a valid number.")
    if not number.is_finite():
        raise CalculationError(f"{label} must be a finite number.")
    return number


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def _rate(value: Decimal) -> float:
    return float(value.quantize(RATE, rounding=ROUND_HALF_UP))


@dataclass
class InvoiceItemInput:
    product_id: int
    quantity: float
    purchase_usd: float
    sale_dzd: float


@dataclass
class InvoiceItemResult:
    product_id: int
    quantity: float
    purchase_usd: float
    purchase_dzd: float
    sale_dzd: float
    total_usd: float
    total_dzd: float
    total_sale: float
    unit_profit: float
    total_profit: float


@dataclass
class InvoiceCalculation:
    total_payments: float = 0.0
    total_discounts: float = 0.0
    net_payments: float = 0.0
    total_expenses: float = 0.0
    net_cost: float = 0.0
    total_usd: float = 0.0
    exchange_rate: float = 0.0
    total_sales: float = 0.0
    total_profit: float = 0.0
    profit_margin: float = 0.0
    items: list[InvoiceItemResult] = field(default_factory=list)


def calculate_invoice(
    items: list[InvoiceItemInput],
    payments: list[float],
    discounts: list[float],
    expenses: list[float],
) -> InvoiceCalculation:
    """
    يحسب كل قيم الفاتورة.

    Raises:
        CalculationError: عند فشل التحقق.
    """
    if not items:
        raise CalculationError("At least one product is required.")

    payment_values = [_decimal(v, "Payment") for v in payments]
    discount_values = [_decimal(v, "Discount") for v in discounts]
    expense_values = [_decimal(v, "Expense") for v in expenses]
    if any(v < 0 for v in payment_values + discount_values + expense_values):
        raise CalculationError("Payments, discounts, and expenses cannot be negative.")

    rounded = lambda value: value.quantize(MONEY, rounding=ROUND_HALF_UP)
    total_payments = sum((rounded(v) for v in payment_values), Decimal("0"))
    total_discounts = sum((rounded(v) for v in discount_values), Decimal("0"))
    total_expenses = sum((rounded(v) for v in expense_values), Decimal("0"))

    if total_discounts > total_payments:
        raise CalculationError("Total discounts cannot exceed total payments.")

    net_payments = total_payments - total_discounts
    net_cost = net_payments + total_expenses

    normalized_items = []
    for item in items:
        quantity = _decimal(item.quantity, "Quantity")
        purchase_usd = _decimal(item.purchase_usd, "Purchase price")
        sale_dzd = _decimal(item.sale_dzd, "Sale price")
        if quantity <= 0:
            raise CalculationError("Quantity must be greater than zero.")
        if purchase_usd <= 0:
            raise CalculationError("Purchase price must be greater than zero.")
        if sale_dzd <= 0:
            raise CalculationError("Sale price must be greater than zero.")
        normalized_items.append((item, quantity, purchase_usd, sale_dzd))

    total_usd = sum(
        (quantity * purchase_usd for _, quantity, purchase_usd, _ in normalized_items),
        Decimal("0"),
    )
    if total_usd <= 0:
        raise CalculationError("Total USD must be greater than zero.")

    exchange_rate = net_cost / total_usd

    results: list[InvoiceItemResult] = []
    total_sales = Decimal("0")
    total_profit = Decimal("0")

    cumulative_cost = Decimal("0")
    allocated_cost = Decimal("0")
    rounded_usd = Decimal("0")
    for it, quantity, purchase_usd, sale_dzd in normalized_items:
        purchase_dzd = purchase_usd * exchange_rate
        item_total_usd = quantity * purchase_usd
        # Allocate rounding cents cumulatively; line costs sum to net_cost.
        cumulative_cost += quantity * purchase_dzd
        next_allocation = rounded(cumulative_cost)
        item_total_dzd = next_allocation - allocated_cost
        allocated_cost = next_allocation
        item_total_sale = rounded(quantity * sale_dzd)
        unit_profit = sale_dzd - purchase_dzd
        item_total_profit = item_total_sale - item_total_dzd
        rounded_usd += rounded(item_total_usd)

        results.append(InvoiceItemResult(
            product_id=it.product_id,
            quantity=float(quantity),
            purchase_usd=float(purchase_usd),
            purchase_dzd=_money(purchase_dzd),
            sale_dzd=float(sale_dzd),
            total_usd=_money(item_total_usd),
            total_dzd=_money(item_total_dzd),
            total_sale=_money(item_total_sale),
            unit_profit=_money(unit_profit),
            total_profit=_money(item_total_profit),
        ))

        total_sales += item_total_sale
        total_profit += item_total_profit

    profit_margin = (total_profit / total_sales * Decimal("100")) if total_sales > 0 else Decimal("0")

    return InvoiceCalculation(
        total_payments=_money(total_payments),
        total_discounts=_money(total_discounts),
        net_payments=_money(net_payments),
        total_expenses=_money(total_expenses),
        net_cost=_money(net_cost),
        total_usd=_money(rounded_usd),
        exchange_rate=_rate(exchange_rate),
        total_sales=_money(total_sales),
        total_profit=_money(total_profit),
        profit_margin=float(profit_margin.quantize(PERCENT, rounding=ROUND_HALF_UP)),
        items=results,
    )
