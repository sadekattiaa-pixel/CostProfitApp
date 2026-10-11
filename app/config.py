"""Application constants and configuration."""

APP_NAME = "Invoice"
APP_NAME_AR = "Invoice"
APP_VERSION = "2.1.0"
APP_AUTHOR = "Alintilqa Programming & Digital Solutions"
APP_COPYRIGHT = "© 2026 Alintilqa Programming & Digital Solutions. All rights reserved."
APP_COPYRIGHT_AR = "© 2026 Alintilqa Programming & Digital Solutions. جميع الحقوق محفوظة."

# Limits
MAX_PRODUCTS_WARNING = 500
MAX_SUPPLIERS = 30
MAX_PAYMENTS_PER_INVOICE = 50
MAX_DISCOUNTS_PER_INVOICE = 50
MAX_EXPENSES_PER_INVOICE = 50
MAX_ITEMS_PER_INVOICE = 100
MAX_LAYOUT_IMAGE_MB = 1
MAX_LOGO_IMAGE_MB = 2

# Security
PASSWORD_MIN_LENGTH = 6
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 60

# Auto-lock
DEFAULT_AUTO_LOCK_MINUTES = 10
HEARTBEAT_INTERVAL_SECONDS = 30
STALE_LOCK_THRESHOLD_MINUTES = 5
AUTO_SAVE_INTERVAL_SECONDS = 30

# Categories
CATEGORIES = ["Batteries", "Car Tires", "Truck Tires"]
CATEGORIES_AR = ["بطاريات", "إطارات سيارات", "إطارات شاحنات"]

# Default expense items
DEFAULT_EXPENSE_ITEMS = [
    "جمرك",
    "نقل",
    "موانئ",
    "شحن",
    "مناولة",
    "ضريبة استيراد",
    "عمولة وسيط",
]

# Currency
CURRENCY_LYD = "د.ل"
CURRENCY_USD = "$"
