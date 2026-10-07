"""
صفحة إنشاء/تحرير فاتورة جديدة — بنظام التبويبات.
"""
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt, QSize, QDate, QObject, QEvent, QStringListModel, QTimer
from PySide6.QtGui import QColor, QDoubleValidator, QPixmap
from PySide6.QtWidgets import (
    QWidget, QTextEdit, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea,
    QTabWidget, QCheckBox, QGridLayout, QCompleter,
)

from app.services.invoice_service import invoice_service, InvoiceError
from app.services.product_service import product_service
from app.services.supplier_service import supplier_service
from app.services.settings_service import settings
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.theme import set_widget_stylesheet


# ============================================================
# مانع عجلة الماوس
# ============================================================
class WheelBlocker(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            event.ignore()
            return True
        return False


_wheel_blocker = WheelBlocker()


# ============================================================
# كل الأعمدة
# ============================================================
ALL_COLUMNS = [
    ("qty",           "Qty",          "Qty",        90,  True),
    ("purchase_usd",  "Price $",   "الشراء $",       110, True),
    ("unit_dzd",      "Unit LYD",     "الوحدة د.ل",     110, True),
    ("sale_dzd",      "Sale LYD",     "البيع د.ل",      110, True),
    ("total_usd",     "Total $",      "الإجمالي $",     110, True),
    ("total_dzd",     "Total LYD",    "الإجمالي د.ل",   120, True),
    ("total_sale",    "Total Sale",   "إجمالي البيع",   120, True),
    ("unit_profit",   "Unit Profit",  "ربح الوحدة",     110, True),
    ("total_profit",  "Profit",       "الربح",          120, True),
    ("code",          "Code",         "الكود",          110, True),
    ("pattern",       "Pattern",      "النقشة",         130, False),
    ("category",      "Category",     "التصنيف",        130, True),
    ("supplier",      "Supplier",     "المورد",         180, True),
    ("image",         "layout",        "layout",         70,  True),
    ("ah",            "AH",           "AH",             60,  False),
    ("l",             "L",            "L",              60,  False),
    ("w",             "W",            "W",              60,  False),
    ("h",             "H",            "H",              60,  False),
    ("oh",            "OH",           "OH",             60,  False),
    ("layout",        "layout",       "layout",        80,  False),
    ("pallet",        "Pallet",       "Pallet",        80,  True),
]

COLUMN_KEYS = [c[0] for c in ALL_COLUMNS]
DEFAULT_VISIBLE = [c[0] for c in ALL_COLUMNS if c[4]]
DEFAULT_WIDTHS = {c[0]: c[3] for c in ALL_COLUMNS}
DEFAULT_WIDTHS["product"] = 280
DEFAULT_WIDTHS["remove"] = 82

ALL_TABS = ["tab_info", "tab_items", "tab_payments", "tab_summary"]
DEFAULT_PRINT_TABS = list(ALL_TABS)


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "title":           ("New Invoice",                "فاتورة جديدة"),
    "title_edit":      ("Edit Draft",                 "تعديل مسودة"),
    "subtitle":        ("Create an independent invoice with automatic calculations.",
                        "أنشئ فاتورة مستقلة بحساب تلقائي."),
    "btn_save_draft":  ("Save Draft",                 "حفظ كمسودة"),
    "btn_archive":     ("Archive",                    "أرشفة"),
    "btn_reset":       ("New",                        "جديدة"),
    "btn_customize":   ("⚙ Customize",                "⚙ تخصيص"),

    "tab_info":        ("Invoice Info",               "بيانات الفاتورة"),
    "tab_items":       ("Products",                   "الأصناف"),
    "tab_payments":    ("Payments & Expenses",        "المدفوعات والمصاريف"),
    "notes": ("Notes (PDF only)", "ملاحظات (تظهر في PDF فقط)"),
    "export_pdf": ("Export PDF", "تصدير PDF"),
    "tab_summary":     ("Summary",                    "الملخص"),

    "sec_supplier":    ("Supplier Information",       "بيانات المورد"),
    "sec_company":     ("Company Information",        "بيانات الشركة"),
    "field_inv_no":    ("Invoice No.",                "رقم الفاتورة"),
    "field_sup_inv":   ("Supplier Inv. No.",          "رقم فاتورة المورد"),
    "field_date":      ("Invoice Date",               "تاريخ الفاتورة"),
    "field_supplier":  ("Supplier",                   "المورد"),
    "field_sup_addr":  ("Supplier Address",           "عنوان المورد"),
    "field_sup_phone": ("Supplier Phone",             "رقم هاتف المورد"),
    "field_sup_email": ("Supplier Email",             "إيميل المورد"),
    "field_com_name":  ("Company Name",               "اسم الشركة"),
    "field_com_addr":  ("Company Address",            "عنوان الشركة"),
    "field_com_phone": ("Company Phone",              "رقم هاتف الشركة"),
    "field_com_email": ("Company Email",              "إيميل الشركة"),
    "select_supplier": ("Select supplier...",         "اختر موردًا..."),

    "btn_add_row":     ("+ Add Product",              "+ إضافة صنف"),
    "col_product":     ("Product",                    "Product"),
    "items_total":     ("TOTAL",                      "الإجمالي"),
    "select_product":  ("Type or select product...",  "اكتب أو اختر صنفًا..."),

    "sec_payments":    ("Payments",                   "الدفعات"),
    "btn_add_payment": ("+ Add Payment",              "+ إضافة دفعة"),
    "sec_discounts":   ("Discounts",                  "الخصومات"),
    "btn_add_discount":("+ Add Discount",             "+ إضافة خصم"),
    "sec_expenses":    ("Additional Expenses",        "المصاريف الإضافية"),
    "btn_add_expense": ("+ Add Expense",              "+ إضافة مصروف"),

    "sum_payments":    ("Total Payments",             "إجمالي الدفعات"),
    "sum_discounts":   ("Total Discounts",            "إجمالي الخصومات"),
    "sum_net":         ("Net Payments",               "صافي المدفوعات"),
    "sum_expenses":    ("Total Expenses",             "إجمالي المصاريف"),
    "sum_cost":        ("Net Cost (LYD)",             "صافي التكلفة (د.ل)"),
    "sum_usd":         ("Total Value (USD)",          "القيمة بالدولار"),
    "sum_pallet":      ("Total Pallets",              "إجمالي الطبلية"),
    "sum_rate":        ("Exchange Rate",              "سعر الصرف"),
    "sum_sales":       ("Total Sales (LYD)",          "إجمالي البيع (د.ل)"),
    "sum_profit":      ("Total Profit (LYD)",         "إجمالي الربح (د.ل)"),
    "sum_margin":      ("Profit Margin",              "هامش الربح"),

    "customize_title": ("Customize",                  "تخصيص"),
    "customize_cols":  ("Visible Columns in Items Table",
                        "الأعمدة الظاهرة في جدول الأصناف"),
    "customize_tabs":  ("Tabs Visible in Print",
                        "التبويبات الظاهرة في الطباعة"),
    "customize_reset": ("Reset to Default",           "استعادة الافتراضي"),
    "btn_apply":       ("Apply",                      "تطبيق"),
    "btn_cancel":      ("Cancel",                     "إلغاء"),

    "err_title":       ("Error",                      "خطأ"),
    "err_supplier":    ("Please select a supplier.",  "الرجاء اختيار مورد."),
    "err_no_items":    ("Add at least one product.",  "أضف صنفًا واحدًا على الأقل."),
    "err_bad_row":     ("Some rows are incomplete.",  "بعض الصفوف غير مكتملة."),
    "warn_title":      ("Warning",                    "تحذير"),
    "confirm_archive_t":("Archive Invoice",           "أرشفة الفاتورة"),
    "confirm_archive_m":("Once archived, this invoice cannot be edited.\nContinue?",
                         "بعد الأرشفة لا يمكن تعديل الفاتورة.\nهل تريد المتابعة؟"),
    "saved_msg":       ("Draft saved.",               "تم حفظ المسودة."),
    "archived_msg":    ("Invoice archived.",          "تم أرشفة الفاتورة."),
    "confirm_reset_t": ("Reset Invoice",              "إعادة تعيين"),
    "confirm_reset_m": ("All unsaved changes will be lost.\nContinue?",
                        "كل التغييرات غير المحفوظة ستفقد.\nهل تريد المتابعة؟"),
    "confirm_sup_change":("Changing supplier will clear products. Continue?",
                          "تغيير المورد سيمسح الأصناف. متابعة؟"),
    "payment_n":       ("Payment",                    "دفعة"),
    "discount_n":      ("Discount",                   "خصم"),
}


def _t(key, language, **kwargs):
    en, ar = TEXTS.get(key, ("", ""))
    text = ar if language == "ar" else en
    if kwargs:
        text = text.format(**kwargs)
    return text


def _fmt_money(v):
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _fmt_num(v):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def _parse_float(text, default=0.0):
    if not text or not text.strip():
        return default
    try:
        return float(text.strip().replace(",", ""))
    except ValueError:
        return default


def _category_label(cat, language):
    from app.config import CATEGORIES, CATEGORIES_AR
    if language == "ar":
        try:
            return CATEGORIES_AR[CATEGORIES.index(cat)]
        except ValueError:
            return cat
    return cat


# ============================================================
# إدخال رقمي عبر QLineEdit — مع إشارة Enter
# ============================================================
class NumericLineEdit(QLineEdit):
    def __init__(self, parent=None, integer_only=False):
        super().__init__(parent)
        self._integer_only = integer_only
        validator = QDoubleValidator(0, 999_999_999, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        if integer_only:
            validator.setDecimals(0)
        self.setValidator(validator)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("")
        self.setMinimumHeight(40)
        self.installEventFilter(_wheel_blocker)

    def value(self) -> float:
        return _parse_float(self.text(), 0.0)

    def set_value(self, val):
        if val is None or val == 0:
            self.setText("")
        else:
            if self._integer_only:
                self.setText(str(int(val)))
            else:
                self.setText(_fmt_num(val))


# ============================================================
# ComboBox قابل للبحث + إشارة Enter
# ============================================================
class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumHeight(40)
        self.installEventFilter(_wheel_blocker)

        self._completer = QCompleter(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self._completer)

        self.lineEdit().textEdited.connect(self._on_text_edited)

    def _on_text_edited(self, text):
        if text:
            self._completer.setCompletionPrefix(text)
            self._completer.complete()
        else:
            self._completer.popup().hide()

    def current_product_id(self):
        text = self.currentText().strip()
        if not text:
            return None
        for i in range(self.count()):
            if self.itemText(i) == text:
                return self.itemData(i)
        for i in range(self.count()):
            item_text = self.itemText(i)
            if item_text and item_text.startswith(text):
                return self.itemData(i)
        return None


# ============================================================
# نافذة تخصيص
# ============================================================
class CustomizeDialog(QDialog):

    def __init__(self, parent, language, visible_cols, print_tabs):
        super().__init__(parent)
        self.language = language
        self.visible_cols = set(visible_cols)
        self.print_tabs = set(print_tabs)
        self.col_checkboxes = {}
        self.tab_checkboxes = {}
        self.setWindowTitle(_t("customize_title", language))
        self.setModal(True)
        self.setMinimumWidth(600)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

        title = QLabel(_t("customize_title", self.language))
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        lbl1 = QLabel(_t("customize_cols", self.language))
        lbl1.setObjectName("SectionLabel")
        layout.addWidget(lbl1)

        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (key, en, ar, _w, _vis) in enumerate(ALL_COLUMNS):
            cb = QCheckBox(ar if self.language == "ar" else en)
            cb.setChecked(key in self.visible_cols)
            self.col_checkboxes[key] = cb
            grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(grid)

        sep = QFrame(); sep.setFixedHeight(1); sep.setObjectName("Sep")
        layout.addWidget(sep)

        lbl2 = QLabel(_t("customize_tabs", self.language))
        lbl2.setObjectName("SectionLabel")
        layout.addWidget(lbl2)

        tabs_grid = QGridLayout()
        tabs_grid.setSpacing(6)
        for i, key in enumerate(ALL_TABS):
            cb = QCheckBox(_t(key, self.language))
            cb.setChecked(key in self.print_tabs)
            self.tab_checkboxes[key] = cb
            tabs_grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(tabs_grid)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setObjectName("Sep")
        layout.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        reset_btn = QPushButton(_t("customize_reset", self.language))
        reset_btn.setObjectName("SecondaryBtn")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setMinimumHeight(38)
        reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()

        cancel_btn = QPushButton(_t("btn_cancel", self.language))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(38); cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton(_t("btn_apply", self.language))
        apply_btn.setObjectName("PrimaryBtn")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.setMinimumHeight(38); apply_btn.setMinimumWidth(120)
        apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

    def _on_reset(self):
        for key, cb in self.col_checkboxes.items():
            cb.setChecked(key in DEFAULT_VISIBLE)
        for key, cb in self.tab_checkboxes.items():
            cb.setChecked(key in DEFAULT_PRINT_TABS)

    def get_visible_columns(self):
        return [c[0] for c in ALL_COLUMNS if self.col_checkboxes[c[0]].isChecked()]

    def get_print_tabs(self):
        return [k for k in ALL_TABS if self.tab_checkboxes[k].isChecked()]

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QLabel#DialogTitle { color: #FFFFFF; font-size: 20px; font-weight: 700; background: transparent; }
            QLabel#SectionLabel { color: #60A5FA; font-size: 14px; font-weight: 600; background: transparent; padding-top: 6px; }
            QFrame#Sep { background-color: rgba(37, 99, 235, 0.25); border: none; }
            QCheckBox { color: #FFFFFF; font-size: 14px; spacing: 8px; padding: 6px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(37, 99, 235, 0.5); background-color: rgba(15, 29, 53, 0.9); }
            QCheckBox::indicator:checked { background-color: #2563EB; border: 1px solid #2563EB; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: transparent; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(255,255,255,0.06); }
        """)


# ============================================================
# صف مبلغ
# ============================================================
class AmountRow(QFrame):
    def __init__(self, parent_dialog, label="", amount=0.0):
        super().__init__()
        self.setObjectName("AmountRow")
        self.parent_dialog = parent_dialog
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.label_input = QLineEdit(label)
        self.label_input.setPlaceholderText("Label")
        self.label_input.setMinimumHeight(38)
        self.label_input.installEventFilter(_wheel_blocker)
        layout.addWidget(self.label_input, 1)

        self.amount_input = NumericLineEdit(self)
        if amount:
            self.amount_input.setText(_fmt_num(amount))
        self.amount_input.textChanged.connect(self.parent_dialog._recalculate)
        layout.addWidget(self.amount_input, 1)

        btn = QPushButton("✕")
        btn.setObjectName("RemoveBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(32, 32)
        btn.clicked.connect(self._remove)
        layout.addWidget(btn)

    def _remove(self):
        self.parent_dialog._remove_amount_row(self)

    def get_data(self):
        return {
            "label": self.label_input.text().strip(),
            "amount": self.amount_input.value(),
        }


class ItemRowWidget(QWidget):
    def __init__(self, page, row_index):
        super().__init__()
        self.page = page
        self.row_index = row_index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copy_btn = QPushButton("⧉")
        self.copy_btn.setObjectName("RemoveRowBtn")
        self.copy_btn.setToolTip("نسخ الصف" if page.language == "ar" else "Duplicate row")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setFixedSize(32, 32)
        self.copy_btn.clicked.connect(lambda: page._duplicate_item_row(self.row_index))
        layout.addWidget(self.copy_btn)

        self.btn = QPushButton("🗑")
        self.btn.setObjectName("RemoveRowBtn")
        self.btn.setToolTip("حذف الصف" if page.language == "ar" else "Delete row")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setFixedSize(32, 32)
        self.btn.clicked.connect(lambda: page._remove_item_row(self.row_index))
        layout.addWidget(self.btn)


# ============================================================
# الصفحة الرئيسية
# ============================================================
class InvoicePage(QWidget):

    def __init__(self, theme="dark", language="en", invoice_id=None):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.invoice_id = invoice_id
        self.current_supplier_id = None
        self._amount_rows_payments = []
        self._amount_rows_discounts = []
        self._amount_rows_expenses = []
        self._item_rows = []

        self.visible_columns = self._load_visible_columns()
        self.print_tabs = self._load_print_tabs()
        self.column_widths = self._load_column_widths()

        self._build_ui()
        self._apply_style()
        self._reload_texts()

        if invoice_id:
            self._load_invoice(invoice_id)
        else:
            self._reset_form()

    def _load_visible_columns(self):
        try:
            raw = settings.get("invoice_visible_columns", "")
            if raw:
                data = json.loads(raw)
                if isinstance(data, list):
                    columns = [k for k in data if k in COLUMN_KEYS]
                    if "pallet" not in columns:
                        columns.append("pallet")
                    return columns
        except Exception:
            pass
        return list(DEFAULT_VISIBLE)

    def _save_visible_columns(self):
        try:
            settings.set("invoice_visible_columns", json.dumps(self.visible_columns))
        except Exception:
            pass

    def _load_print_tabs(self):
        try:
            raw = settings.get("invoice_print_tabs", "")
            if raw:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [k for k in data if k in ALL_TABS]
        except Exception:
            pass
        return list(DEFAULT_PRINT_TABS)

    def _save_print_tabs(self):
        try:
            settings.set("invoice_print_tabs", json.dumps(self.print_tabs))
        except Exception:
            pass

    def _load_column_widths(self):
        try:
            raw = settings.get("invoice_column_widths", "")
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return {k: int(v) for k, v in data.items()
                            if k in COLUMN_KEYS or k in ("product", "remove")}
        except Exception:
            pass
        return dict(DEFAULT_WIDTHS)

    def _save_column_widths(self):
        try:
            settings.set("invoice_column_widths", json.dumps(self.column_widths))
        except Exception:
            pass

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(24, 16, 24, 16)

        text_col = QVBoxLayout(); text_col.setSpacing(2)
        self.header_title = QLabel(""); self.header_title.setObjectName("PageTitle")
        text_col.addWidget(self.header_title)
        self.header_sub = QLabel(""); self.header_sub.setObjectName("PageSub")
        text_col.addWidget(self.header_sub)
        header_layout.addLayout(text_col)
        header_layout.addStretch()

        self.reset_btn = QPushButton("")
        self.reset_btn.setObjectName("SecondaryBtn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setMinimumHeight(42)
        self.reset_btn.clicked.connect(self._on_reset)

        self.save_btn = QPushButton("")
        self.save_btn.setObjectName("SecondaryBtn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setMinimumHeight(42)
        self.save_btn.setIcon(make_icon("invoice", color=self.palette_data["primary"] if self.theme == "light" else "#FFFFFF", size=16))
        self.save_btn.setIconSize(QSize(16, 16))
        self.save_btn.clicked.connect(self._on_save_draft)

        self.archive_btn = QPushButton("")
        self.archive_btn.setObjectName("PrimaryBtn")
        self.archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.archive_btn.setMinimumHeight(42)
        self.archive_btn.setIcon(make_icon("archive", color="#FFFFFF", size=16))
        self.archive_btn.setIconSize(QSize(16, 16))
        self.archive_btn.clicked.connect(self._on_archive)

        self.pdf_btn = QPushButton()
        self.pdf_btn.setObjectName("SecondaryBtn")
        self.pdf_btn.clicked.connect(self._on_export_pdf)
        header_layout.addWidget(self.pdf_btn)
        header_layout.addWidget(self.reset_btn)
        header_layout.addWidget(self.save_btn)
        header_layout.addWidget(self.archive_btn)
        outer.addWidget(header_card)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("InvoiceTabs")
        outer.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_info_tab(), "")
        self.tabs.addTab(self._build_items_tab(), "")
        self.tabs.addTab(self._build_payments_tab(), "")
        self.tabs.addTab(self._build_summary_tab(), "")

    def _build_info_tab(self):
        w = QWidget(); w.setObjectName("TabContent")
        wl = QVBoxLayout(w)
        wl.setContentsMargins(24, 20, 24, 24)
        wl.setSpacing(16)

        row = QHBoxLayout(); row.setSpacing(16)

        # Supplier Card
        sup_card = QFrame(); sup_card.setObjectName("Card")
        sl = QVBoxLayout(sup_card)
        sl.setContentsMargins(24, 20, 24, 20); sl.setSpacing(14)
        self.sec_supplier_lbl = QLabel(""); self.sec_supplier_lbl.setObjectName("CardTitle")
        sl.addWidget(self.sec_supplier_lbl)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_sup_inv_input = QLabel(""); self.lbl_sup_inv_input.setObjectName("FieldLabel")
        box.addWidget(self.lbl_sup_inv_input)
        self.sup_inv_input = QLineEdit()
        self.sup_inv_input.setMinimumHeight(44)
        self.sup_inv_input.installEventFilter(_wheel_blocker)
        box.addWidget(self.sup_inv_input)
        sl.addLayout(box)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_supplier_combo = QLabel(""); self.lbl_supplier_combo.setObjectName("FieldLabel")
        box.addWidget(self.lbl_supplier_combo)
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumHeight(44)
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)
        self.supplier_combo.installEventFilter(_wheel_blocker)
        box.addWidget(self.supplier_combo)
        sl.addLayout(box)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_sup_addr_input = QLabel(""); self.lbl_sup_addr_input.setObjectName("FieldLabel")
        box.addWidget(self.lbl_sup_addr_input)
        self.sup_addr_input = QLineEdit()
        self.sup_addr_input.setReadOnly(True)
        self.sup_addr_input.setMinimumHeight(44)
        self.sup_addr_input.setObjectName("ReadOnlyInput")
        box.addWidget(self.sup_addr_input)
        sl.addLayout(box)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_sup_phone_input = QLabel(""); self.lbl_sup_phone_input.setObjectName("FieldLabel")
        box.addWidget(self.lbl_sup_phone_input)
        self.sup_phone_input = QLineEdit()
        self.sup_phone_input.setReadOnly(True)
        self.sup_phone_input.setMinimumHeight(44)
        self.sup_phone_input.setObjectName("ReadOnlyInput")
        box.addWidget(self.sup_phone_input)
        sl.addLayout(box)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_sup_email_input = QLabel(""); self.lbl_sup_email_input.setObjectName("FieldLabel")
        box.addWidget(self.lbl_sup_email_input)
        self.sup_email_input = QLineEdit()
        self.sup_email_input.setReadOnly(True)
        self.sup_email_input.setMinimumHeight(44)
        self.sup_email_input.setObjectName("ReadOnlyInput")
        box.addWidget(self.sup_email_input)
        sl.addLayout(box)

        sl.addStretch()
        row.addWidget(sup_card, 1)

        # Company Card
        com_card = QFrame(); com_card.setObjectName("Card")
        cl = QVBoxLayout(com_card)
        cl.setContentsMargins(24, 20, 24, 20); cl.setSpacing(14)
        self.sec_company_lbl = QLabel(""); self.sec_company_lbl.setObjectName("CardTitle")
        cl.addWidget(self.sec_company_lbl)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_date = QLabel(""); self.lbl_date.setObjectName("FieldLabel")
        box.addWidget(self.lbl_date)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setMinimumHeight(44)
        self.date_input.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
        self.date_input.installEventFilter(_wheel_blocker)
        box.addWidget(self.date_input)
        cl.addLayout(box)

        box = QVBoxLayout(); box.setSpacing(6)
        self.lbl_inv_no = QLabel(""); self.lbl_inv_no.setObjectName("FieldLabel")
        box.addWidget(self.lbl_inv_no)
        self.inv_no_input = QLineEdit()
        self.inv_no_input.setReadOnly(True)
        self.inv_no_input.setMinimumHeight(44)
        self.inv_no_input.setObjectName("ReadOnlyInput")
        box.addWidget(self.inv_no_input)
        cl.addLayout(box)

        for attr, text_key in [
            ("com_name_input", "field_com_name"),
            ("com_addr_input", "field_com_addr"),
            ("com_phone_input", "field_com_phone"),
            ("com_email_input", "field_com_email"),
        ]:
            box = QVBoxLayout(); box.setSpacing(6)
            lbl = QLabel(""); lbl.setObjectName("FieldLabel")
            setattr(self, f"lbl_{attr}", lbl)
            box.addWidget(lbl)
            widget = QLineEdit()
            widget.setReadOnly(True)
            widget.setMinimumHeight(44)
            widget.setObjectName("ReadOnlyInput")
            setattr(self, attr, widget)
            box.addWidget(widget)
            cl.addLayout(box)

        cl.addStretch()
        row.addWidget(com_card, 1)

        wl.addLayout(row)
        return w

    def _build_items_tab(self):
        w = QWidget(); w.setObjectName("TabContent")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        card = QFrame(); card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18); cl.setSpacing(12)

        top = QHBoxLayout(); top.setSpacing(10)
        self.items_title = QLabel(""); self.items_title.setObjectName("CardTitle")
        top.addWidget(self.items_title); top.addStretch()

        self.customize_cols_btn = QPushButton("")
        self.customize_cols_btn.setObjectName("SecondaryBtn")
        self.customize_cols_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.customize_cols_btn.setMinimumHeight(38)
        self.customize_cols_btn.clicked.connect(self._on_customize)
        top.addWidget(self.customize_cols_btn)

        self.add_row_btn = QPushButton("")
        self.add_row_btn.setObjectName("SecondaryBtn")
        self.add_row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_row_btn.setMinimumHeight(38)
        self.add_row_btn.clicked.connect(self._on_add_item_row)
        top.addWidget(self.add_row_btn)
        cl.addLayout(top)

        self.items_table = QTableWidget()
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setShowGrid(False)
        self.items_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.items_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.items_table.verticalHeader().setDefaultSectionSize(64)
        self.items_table.setMinimumHeight(320)
        self.items_table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        cl.addWidget(self.items_table)

        layout.addWidget(card, 1)
        return w

    def _on_column_resized(self, index, old_size, new_size):
        if not hasattr(self, "_col_keys") or index >= len(self._col_keys):
            return
        key = self._col_keys[index]
        if key == "remove":
            return
        self.column_widths[key] = new_size
        self._save_column_widths()

    def _rebuild_items_table_columns(self):
        columns = [("product", _t("col_product", self.language))]
        for key in self.visible_columns:
            for c in ALL_COLUMNS:
                if c[0] == key:
                    columns.append((key, c[2] if self.language == "ar" else c[1]))
                    break
        columns.append(("remove", ""))

        self.items_table.setColumnCount(len(columns))
        self.items_table.setHorizontalHeaderLabels([c[1] for c in columns])
        self._col_keys = [c[0] for c in columns]
        self._col_index = {k: i for i, k in enumerate(self._col_keys)}

        h = self.items_table.horizontalHeader()
        for i, (key, _) in enumerate(columns):
            if key == "remove":
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.items_table.setColumnWidth(i, 82)
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                saved = self.column_widths.get(key)
                if saved:
                    self.items_table.setColumnWidth(i, saved)
                elif key == "product":
                    self.items_table.setColumnWidth(i, 280)
                else:
                    for c in ALL_COLUMNS:
                        if c[0] == key:
                            self.items_table.setColumnWidth(i, c[3])
                            break
        self._ensure_total_row()

    def _build_payments_tab(self):
        outer = QWidget(); outer.setObjectName("TabContent")
        ol = QVBoxLayout(outer); ol.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ol.addWidget(scroll)

        w = QWidget(); scroll.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 24); layout.setSpacing(16)

        for attr_title, attr_btn, attr_cont, attr_tot, add_handler in [
            ("payments_title", "add_payment_btn", "payments_container", "payments_total", self._on_add_payment),
            ("discounts_title", "add_discount_btn", "discounts_container", "discounts_total", self._on_add_discount),
            ("expenses_title", "add_expense_btn", "expenses_container", "expenses_total", self._on_add_expense),
        ]:
            card = QFrame(); card.setObjectName("Card")
            cl = QVBoxLayout(card); cl.setContentsMargins(20, 18, 20, 18); cl.setSpacing(10)

            top = QHBoxLayout()
            title = QLabel(""); title.setObjectName("CardTitle")
            setattr(self, attr_title, title)
            top.addWidget(title); top.addStretch()

            btn = QPushButton("")
            btn.setObjectName("SecondaryBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(34)
            btn.clicked.connect(add_handler)
            setattr(self, attr_btn, btn)
            top.addWidget(btn)
            cl.addLayout(top)

            container = QVBoxLayout(); container.setSpacing(6)
            setattr(self, attr_cont, container)
            cl.addLayout(container)

            total = QLabel("0.00")
            total.setObjectName("TotalValue")
            total.setAlignment(Qt.AlignmentFlag.AlignRight)
            setattr(self, attr_tot, total)
            cl.addWidget(total)

            layout.addWidget(card)

        layout.addStretch()
        return outer

    def _build_summary_tab(self):
        w = QWidget(); w.setObjectName("TabContent")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 24); layout.setSpacing(16)

        card = QFrame(); card.setObjectName("SummaryCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 24, 28, 26); cl.setSpacing(12)

        self.summary_title = QLabel(""); self.summary_title.setObjectName("CardTitle")
        cl.addWidget(self.summary_title); cl.addSpacing(6)

        self._summary_rows = {}
        self._summary_keys_order = [
            "sum_payments", "sum_discounts", "sum_net",
            "sum_expenses", "sum_cost", "sum_usd", "sum_pallet", "sum_rate",
            "sum_sales", "sum_profit", "sum_margin",
        ]
        for key in self._summary_keys_order:
            row = QHBoxLayout(); row.setSpacing(8)
            lbl = QLabel(""); lbl.setObjectName("SummaryLabel")
            row.addWidget(lbl); row.addStretch()
            val = QLabel("0.00"); val.setObjectName("SummaryValue")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(val)
            cl.addLayout(row)
            self._summary_rows[key] = lbl
            self._summary_rows[key + "__value"] = val
            if key in ("sum_net", "sum_cost"):
                sep = QFrame(); sep.setFixedHeight(1); sep.setObjectName("Sep")
                cl.addWidget(sep)
        self._summary_rows["sum_profit__value"].setObjectName("SummaryProfit")
        self._summary_rows["sum_cost__value"].setObjectName("SummaryCost")

        layout.addWidget(card); layout.addStretch()
        return w

    def _reload_texts(self):
        lang = self.language
        is_edit = self.invoice_id is not None

        self.header_title.setText(_t("title_edit" if is_edit else "title", lang))
        self.header_sub.setText(_t("subtitle", lang))
        self.reset_btn.setText(_t("btn_reset", lang))
        self.save_btn.setText(_t("btn_save_draft", lang))
        self.archive_btn.setText(_t("btn_archive", lang))

        self.tabs.setTabText(0, _t("tab_info", lang))
        self.tabs.setTabText(1, _t("tab_items", lang))
        self.tabs.setTabText(2, _t("tab_payments", lang))
        self.tabs.setTabText(3, _t("tab_summary", lang))

        self.sec_supplier_lbl.setText(_t("sec_supplier", lang))
        self.lbl_sup_inv_input.setText(_t("field_sup_inv", lang))
        self.lbl_supplier_combo.setText(_t("field_supplier", lang))
        self.lbl_sup_addr_input.setText(_t("field_sup_addr", lang))
        self.lbl_sup_phone_input.setText(_t("field_sup_phone", lang))
        self.lbl_sup_email_input.setText(_t("field_sup_email", lang))

        self.sec_company_lbl.setText(_t("sec_company", lang))
        self.lbl_date.setText(_t("field_date", lang))
        self.lbl_inv_no.setText(_t("field_inv_no", lang))
        self.lbl_com_name_input.setText(_t("field_com_name", lang))
        self.lbl_com_addr_input.setText(_t("field_com_addr", lang))
        self.lbl_com_phone_input.setText(_t("field_com_phone", lang))
        self.lbl_com_email_input.setText(_t("field_com_email", lang))

        self.items_title.setText(_t("tab_items", lang))
        self.customize_cols_btn.setText(_t("btn_customize", lang))
        self.add_row_btn.setText(_t("btn_add_row", lang))

        self.payments_title.setText(_t("sec_payments", lang))
        self.add_payment_btn.setText(_t("btn_add_payment", lang))
        self.discounts_title.setText(_t("sec_discounts", lang))
        self.add_discount_btn.setText(_t("btn_add_discount", lang))
        self.expenses_title.setText(_t("sec_expenses", lang))
        self.add_expense_btn.setText(_t("btn_add_expense", lang))

        self.pdf_btn.setText(_t("export_pdf", lang))
        self.summary_title.setText(_t("tab_summary", lang))
        for key in self._summary_keys_order:
            self._summary_rows[key].setText(_t(key, lang))

        self._reload_suppliers()
        self._reload_company_info()

        self._rebuild_items_table_columns()
        if self._item_rows:
            rows_data = []
            for row in self._item_rows:
                pid = row["product_combo"].current_product_id()
                qty = row["qty"].value()
                pu = row["purchase"].value()
                sd = row["sale"].value()
                rows_data.append((pid, qty, pu, sd, self._pallet_value(row), row.get("product_snapshot")))
            self._clear_all_items()
            for pid, qty, pu, sd, pallet, snapshot in rows_data:
                self._add_item_row(product_id=pid, qty=qty, purchase=pu, sale=sd, pallet=pallet, product_snapshot=snapshot)
                self._item_rows[-1]["pallet_input"].setText("" if pallet is None else str(pallet))

    def _reload_suppliers(self):
        current = self.current_supplier_id
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.clear()
        self.supplier_combo.addItem(_t("select_supplier", self.language), None)
        for s in supplier_service.get_all(sort="name_asc"):
            self.supplier_combo.addItem(s["name"], s["id"])
        if current:
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == current:
                    self.supplier_combo.setCurrentIndex(i); break
        copied = getattr(self, "_copied_invoice", None)
        if copied and copied["supplier_id"] == current:
            self.supplier_combo.setItemText(self.supplier_combo.currentIndex(), copied["supplier_name"])
        self.supplier_combo.blockSignals(False)

    def _reload_company_info(self):
        copied = getattr(self, "_copied_invoice", None)
        company = copied.get("_company_snapshot") if copied else None
        if company is not None:
            for field, key in ((self.com_name_input, "company_name"), (self.com_addr_input, "company_address"), (self.com_phone_input, "company_phone"), (self.com_email_input, "company_email")):
                field.setText(company.get(key) or "—")
            return
        self.com_name_input.setText(settings.get("company_name") or "—")
        self.com_addr_input.setText(settings.get("company_address") or "—")
        self.com_phone_input.setText(settings.get("company_phone") or "—")
        self.com_email_input.setText(settings.get("company_email") or "—")

    def _update_supplier_fields(self, supplier_id):
        if not supplier_id:
            for inp in (self.sup_addr_input, self.sup_phone_input, self.sup_email_input):
                inp.setText("")
            return
        copied = getattr(self, "_copied_invoice", None)
        if copied and copied["supplier_id"] == supplier_id:
            for field, key in ((self.sup_addr_input, "supplier_address"), (self.sup_phone_input, "supplier_phone"), (self.sup_email_input, "supplier_email")):
                field.setText(copied.get(key) or "—")
            return
        sup = supplier_service.get_by_id(supplier_id)
        if not sup:
            return
        self.sup_addr_input.setText(sup.get("address") or "—")
        self.sup_phone_input.setText(sup.get("phone") or "—")
        self.sup_email_input.setText(sup.get("email") or "—")

    def _on_customize(self):
        dlg = CustomizeDialog(self, self.language, self.visible_columns, self.print_tabs)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_cols = dlg.get_visible_columns()
        if not new_cols:
            QMessageBox.warning(self, _t("warn_title", self.language),
                "Select at least one column." if self.language != "ar"
                else "اختر عمودًا واحدًا على الأقل.")
            return
        self.visible_columns = new_cols
        self._save_visible_columns()
        self.print_tabs = dlg.get_print_tabs()
        self._save_print_tabs()

        rows_data = []
        for row in self._item_rows:
            pid = row["product_combo"].current_product_id()
            qty = row["qty"].value()
            pu = row["purchase"].value()
            sd = row["sale"].value()
            rows_data.append((pid, qty, pu, sd, self._pallet_value(row), row.get("product_snapshot")))
        self._rebuild_items_table_columns()
        self._clear_all_items()
        for pid, qty, pu, sd, pallet, snapshot in rows_data:
            self._add_item_row(product_id=pid, qty=qty, purchase=pu, sale=sd, pallet=pallet, product_snapshot=snapshot)
            self._item_rows[-1]["pallet_input"].setText("" if pallet is None else str(pallet))

    def _on_supplier_changed(self):
        new_id = self.supplier_combo.currentData()
        if new_id != self.current_supplier_id and self._item_rows:
            if new_id:
                reply = QMessageBox.question(self, _t("warn_title", self.language),
                    _t("confirm_sup_change", self.language),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    self.supplier_combo.blockSignals(True)
                    for i in range(self.supplier_combo.count()):
                        if self.supplier_combo.itemData(i) == self.current_supplier_id:
                            self.supplier_combo.setCurrentIndex(i); break
                    self.supplier_combo.blockSignals(False)
                    return
        self.current_supplier_id = new_id
        self._update_supplier_fields(new_id)
        if new_id:
            self._clear_all_items()
        self._recalculate()

    def _on_add_item_row(self):
        if not self.current_supplier_id:
            QMessageBox.information(self, _t("warn_title", self.language),
                _t("err_supplier", self.language))
            return
        self._add_item_row()
        QTimer.singleShot(50, self._focus_last_product)

    def _focus_last_product(self):
        if self._item_rows:
            last_row = self._item_rows[-1]
            last_row["product_combo"].setFocus()

    def _connect_enter_navigation(self, row_data):
        """يربط حقل Enter بحيث ينتقل المؤشر للحقل التالي."""
        product_combo = row_data["product_combo"]
        qty_input = row_data["qty"]
        purchase_input = row_data["purchase"]
        sale_input = row_data["sale"]

        def product_enter():
            pid = product_combo.current_product_id()
            if pid:
                self._on_product_selected(row_data)
            QTimer.singleShot(0, qty_input.setFocus)

        product_combo.lineEdit().returnPressed.connect(product_enter)

        qty_input.returnPressed.connect(
            lambda: QTimer.singleShot(0, purchase_input.setFocus)
        )
        purchase_input.returnPressed.connect(
            lambda: QTimer.singleShot(0, sale_input.setFocus)
        )

        def sale_enter():
            QTimer.singleShot(0, self._on_add_item_row)

        sale_input.returnPressed.connect(sale_enter)

    def _add_item_row(self, product_id=None, qty=None, purchase=None, sale=None,
                      pallet=None, insert_at=None, product_snapshot=None):
        row_idx = len(self._item_rows) if insert_at is None else max(
            0, min(int(insert_at), len(self._item_rows))
        )
        self.items_table.insertRow(row_idx)

        row_data = {"product_snapshot": product_snapshot}

        product_combo = SearchableComboBox()
        product_combo.setPlaceholderText(_t("select_product", self.language))
        product_combo.addItem("", None)
        if self.current_supplier_id:
            prods = product_service.get_all(supplier_id=self.current_supplier_id, sort="name_asc")
            for p in prods:
                product_combo.addItem(p["name"] + (" — " + p["pattern"] if p.get("pattern") else ""), p["id"])

        # Historical/imported invoices may contain a product whose supplier no
        # longer matches the invoice supplier. Keep it visible instead of
        # rendering a blank product field.
        if product_id and not any(
            product_combo.itemData(i) == product_id
            for i in range(product_combo.count())
        ):
            selected_product = product_service.get_by_id(product_id)
            if selected_product:
                product_combo.addItem(selected_product["name"] + (" — " + selected_product["pattern"] if selected_product.get("pattern") else ""), selected_product["id"])

        if product_snapshot:
            for index in range(product_combo.count()):
                if product_combo.itemData(index) == product_id:
                    product_combo.setItemText(index, product_snapshot.get("product_name", "") + (" — " + product_snapshot["product_pattern"] if product_snapshot.get("product_pattern") else ""))
                    break

        strings = [product_combo.itemText(i) for i in range(product_combo.count())
                   if product_combo.itemText(i)]
        product_combo.completer().setModel(QStringListModel(strings, self))

        product_combo.currentIndexChanged.connect(lambda _, r=row_data: self._on_product_selected(r))
        self.items_table.setCellWidget(row_idx, self._col_index["product"], product_combo)
        row_data["product_combo"] = product_combo
        row_data["product_info"] = None

        qty_input = NumericLineEdit(self, integer_only=True)
        qty_input.textChanged.connect(self._recalculate)
        row_data["qty"] = qty_input

        purchase_input = NumericLineEdit(self)
        purchase_input.textChanged.connect(self._recalculate)
        row_data["purchase"] = purchase_input

        sale_input = NumericLineEdit(self)
        sale_input.textChanged.connect(self._recalculate)
        row_data["sale"] = sale_input

        pallet_input = NumericLineEdit(self, integer_only=True)
        pallet_input.setPlaceholderText("—")
        pallet_input.textChanged.connect(self._recalculate)
        row_data["pallet_input"] = pallet_input

        for k in ["unit_dzd", "total_usd", "total_dzd", "total_sale", "unit_profit", "total_profit"]:
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            row_data[k + "_item"] = item

        for k in ["code", "pattern", "category", "ah", "l", "w", "h", "oh", "layout"]:
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(self.palette_data["text_muted"]) if self.theme == "light" else Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            row_data[k + "_item"] = item

        sup_item = QTableWidgetItem("—")
        sup_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        sup_item.setForeground(QColor(self.palette_data["text_muted"]) if self.theme == "light" else Qt.GlobalColor.lightGray)
        row_data["supplier_item"] = sup_item

        img_widget = QWidget()
        il = QHBoxLayout(img_widget)
        il.setContentsMargins(0, 0, 0, 0)
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lbl = QLabel("—")
        img_lbl.setFixedSize(44, 44)
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_widget_stylesheet(img_lbl, "background-color: rgba(15, 29, 53, 0.7); border: 1px solid rgba(37, 99, 235, 0.25); border-radius: 8px; color: rgba(148,163,184,0.5); font-size: 18px;")
        il.addWidget(img_lbl)
        row_data["image_widget"] = img_widget
        row_data["image_label"] = img_lbl

        remove_widget = ItemRowWidget(self, row_idx)
        row_data["remove_widget"] = remove_widget

        for key, col_idx in self._col_index.items():
            if key == "product":
                continue
            if key == "remove":
                self.items_table.setCellWidget(row_idx, col_idx, remove_widget)
                continue
            if key in ("qty", "purchase_usd", "sale_dzd", "pallet"):
                wk = {
                    "qty": "qty",
                    "purchase_usd": "purchase",
                    "sale_dzd": "sale",
                    "pallet": "pallet_input",
                }[key]
                self.items_table.setCellWidget(row_idx, col_idx, row_data[wk])
                continue
            if key == "image":
                self.items_table.setCellWidget(row_idx, col_idx, img_widget)
                continue
            item = row_data.get(key + "_item")
            if item:
                self.items_table.setItem(row_idx, col_idx, item)

        self._item_rows.insert(row_idx, row_data)
        for i, existing_row in enumerate(self._item_rows):
            existing_row["remove_widget"].row_index = i

        if product_id:
            for i in range(product_combo.count()):
                if product_combo.itemData(i) == product_id:
                    product_combo.setCurrentIndex(i); break
        if qty:
            qty_input.set_value(qty)
        if purchase is not None:
            purchase_input.set_value(purchase)
        if sale:
            sale_input.set_value(sale)
        if pallet is not None:
            pallet_input.setText(str(int(pallet)))

        self._connect_enter_navigation(row_data)

        self._recalculate()

    def _on_product_selected(self, row_data):
        pid = row_data["product_combo"].current_product_id()
        if not pid:
            row_data["product_info"] = None
            row_data["product_snapshot"] = None
            for k in ["code", "pattern", "category", "ah", "l", "w", "h", "oh", "layout", "pallet"]:
                it = row_data.get(k + "_item")
                if it:
                    it.setText("—")
            row_data["pallet_input"].clear()
            row_data["supplier_item"].setText("—")
            row_data["image_label"].setText("—")
            row_data["image_label"].setPixmap(QPixmap())
            self._recalculate()
            return
        snapshot = row_data.get("product_snapshot")
        if snapshot and snapshot.get("product_id") != pid:
            row_data["product_snapshot"] = snapshot = None
        prod = product_service.get_by_id(pid)
        if prod and snapshot:
            prod.update({key.removeprefix("product_"): value for key, value in snapshot.items() if key.startswith("product_")})
            prod["layout_image"] = snapshot.get("product_image")
        row_data["product_info"] = prod
        if prod:
            row_data["purchase"].set_value(
                product_service.get_last_purchase_price(pid)
            )
            row_data["pallet_input"].set_value(prod.get("pallet"))
            for k in ["code", "pattern", "category", "ah", "l", "w", "h", "oh", "layout", "pallet"]:
                it = row_data.get(k + "_item")
                if it:
                    val = prod.get(k)
                    if k in ("code", "pattern"):
                        it.setText(prod.get(k) or "—")
                    elif k == "category":
                        it.setText(_category_label(prod.get("category", ""), self.language))
                    else:
                        it.setText(_fmt_num(val))
            row_data["supplier_item"].setText(prod.get("supplier_name") or "—")
            if prod.get("layout_image"):
                path = product_service.get_image_path(prod["layout_image"])
                if path:
                    pix = QPixmap(str(path))
                    if not pix.isNull():
                        row_data["image_label"].setPixmap(pix.scaled(
                            40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
                    else:
                        row_data["image_label"].setText("📦")
                else:
                    row_data["image_label"].setText("📦")
            else:
                row_data["image_label"].setText("📦")
        self._recalculate()

    def _remove_item_row(self, row_index):
        self._remove_items_table_row(row_index)
        if 0 <= row_index < len(self._item_rows):
            self._item_rows.pop(row_index)
        for i, row in enumerate(self._item_rows):
            row["remove_widget"].row_index = i
        self._recalculate()

    def _duplicate_item_row(self, row_index):
        if not 0 <= row_index < len(self._item_rows):
            return
        source = self._item_rows[row_index]
        self._add_item_row(
            product_id=source["product_combo"].current_product_id(),
            qty=source["qty"].value(),
            purchase=source["purchase"].value(),
            sale=source["sale"].value(),
            pallet=self._pallet_value(source),
            insert_at=row_index + 1,
        )

    def _remove_items_table_row(self, row_index):
        if not 0 <= row_index < self.items_table.rowCount():
            return
        for column_index in range(self.items_table.columnCount()):
            widget = self.items_table.cellWidget(row_index, column_index)
            if widget is not None:
                self.items_table.removeCellWidget(row_index, column_index)
                widget.deleteLater()
        self.items_table.removeRow(row_index)

    def _clear_all_items(self):
        while self.items_table.rowCount() > 0:
            self._remove_items_table_row(0)
        self._item_rows.clear()
        self._ensure_total_row()

    def _ensure_total_row(self):
        total_row = len(self._item_rows)
        if self.items_table.rowCount() <= total_row:
            self.items_table.insertRow(total_row)
        self._update_total_row()

    def _update_total_row(self, totals=None):
        if not hasattr(self, "_col_index") or not self._col_index:
            return

        total_row = len(self._item_rows)
        if self.items_table.rowCount() <= total_row:
            self.items_table.insertRow(total_row)

        totals = totals or {}
        for key, col_idx in self._col_index.items():
            if key == "remove":
                continue
            if key == "product":
                text = _t("items_total", self.language)
            elif key == "qty":
                text = _fmt_num(totals.get("qty", 0))
            elif key == "pallet":
                text = _fmt_num(totals.get("pallet", 0))
            elif key in ("total_usd", "total_dzd", "total_sale", "total_profit"):
                text = _fmt_money(totals.get(key, 0))
            else:
                text = ""

            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QColor(self.palette_data["bg_elevated"]))
            item.setForeground(QColor(self.palette_data["text"]))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self.items_table.setItem(total_row, col_idx, item)

    def _on_add_payment(self):
        n = len(self._amount_rows_payments) + 1
        row = AmountRow(self, label=f"{_t('payment_n', self.language)} {n}")
        self._amount_rows_payments.append(row)
        self.payments_container.addWidget(row)
        self._recalculate()

    def _on_add_discount(self):
        n = len(self._amount_rows_discounts) + 1
        row = AmountRow(self, label=f"{_t('discount_n', self.language)} {n}")
        self._amount_rows_discounts.append(row)
        self.discounts_container.addWidget(row)
        self._recalculate()

    def _on_add_expense(self):
        row = AmountRow(self, label="")
        self._amount_rows_expenses.append(row)
        self.expenses_container.addWidget(row)
        self._recalculate()

    def _remove_amount_row(self, row):
        if row in self._amount_rows_payments:
            self._amount_rows_payments.remove(row)
        elif row in self._amount_rows_discounts:
            self._amount_rows_discounts.remove(row)
        elif row in self._amount_rows_expenses:
            self._amount_rows_expenses.remove(row)
        row.setParent(None); row.deleteLater()
        self._recalculate()

    def _collect_items(self):
        items = []
        for row in self._item_rows:
            pid = row["product_combo"].current_product_id()
            qty = row["qty"].value()
            pu = row["purchase"].value()
            sd = row["sale"].value()
            if pid and qty > 0 and pu > 0 and sd > 0:
                items.append({
                    "product_id": pid, "quantity": qty,
                    "purchase_usd": pu, "sale_dzd": sd, "row": row,
                })
        return items

    def _collect_amounts(self, rows):
        return [r.get_data() for r in rows]

    def _recalculate(self):
        valid_items = self._collect_items()
        payments = self._collect_amounts(self._amount_rows_payments)
        discounts = self._collect_amounts(self._amount_rows_discounts)
        expenses = self._collect_amounts(self._amount_rows_expenses)

        total_payments = sum(p["amount"] for p in payments)
        total_discounts = sum(d["amount"] for d in discounts)
        total_expenses = sum(e["amount"] for e in expenses)
        net_payments = total_payments - total_discounts
        net_cost = net_payments + total_expenses

        self.payments_total.setText(f"{_fmt_money(total_payments)} د.ل")
        self.discounts_total.setText(f"{_fmt_money(total_discounts)} د.ل")
        self.expenses_total.setText(f"{_fmt_money(total_expenses)} د.ل")

        total_usd = sum(it["quantity"] * it["purchase_usd"] for it in valid_items)
        exchange_rate = (net_cost / total_usd) if total_usd > 0 else 0

        total_sales = 0.0
        total_profit = 0.0
        total_quantity = 0.0
        total_pallet = sum((self._pallet_value(row) or 0) for row in self._item_rows)

        for it in valid_items:
            row = it["row"]
            unit_dzd = it["purchase_usd"] * exchange_rate
            item_total_usd = it["quantity"] * it["purchase_usd"]
            item_total_dzd = it["quantity"] * unit_dzd
            item_total_sale = it["quantity"] * it["sale_dzd"]
            unit_profit = it["sale_dzd"] - unit_dzd
            item_total_profit = it["quantity"] * unit_profit

            row["unit_dzd_item"].setText(_fmt_money(unit_dzd))
            row["total_usd_item"].setText(_fmt_money(item_total_usd))
            row["total_dzd_item"].setText(_fmt_money(item_total_dzd))
            row["total_sale_item"].setText(_fmt_money(item_total_sale))
            row["unit_profit_item"].setText(_fmt_money(unit_profit))
            row["total_profit_item"].setText(_fmt_money(item_total_profit))
            row["total_profit_item"].setForeground(
                Qt.GlobalColor.red if item_total_profit < 0 else (QColor(self.palette_data["text"]) if self.theme == "light" else Qt.GlobalColor.white))

            total_sales += item_total_sale
            total_profit += item_total_profit
            total_quantity += it["quantity"]

        profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0

        self._update_total_row({
            "qty": total_quantity,
            "pallet": total_pallet,
            "total_usd": total_usd,
            "total_dzd": sum(it["quantity"] * it["purchase_usd"] * exchange_rate for it in valid_items),
            "total_sale": total_sales,
            "total_profit": total_profit,
        })

        self._set_summary("sum_payments", f"{_fmt_money(total_payments)} د.ل")
        self._set_summary("sum_discounts", f"- {_fmt_money(total_discounts)} د.ل")
        self._set_summary("sum_net", f"{_fmt_money(net_payments)} د.ل")
        self._set_summary("sum_expenses", f"+ {_fmt_money(total_expenses)} د.ل")
        self._set_summary("sum_cost", f"{_fmt_money(net_cost)} د.ل")
        self._set_summary("sum_usd", f"$ {_fmt_money(total_usd)}")
        self._set_summary("sum_pallet", _fmt_num(total_pallet))
        self._set_summary("sum_rate", f"{exchange_rate:.4f}")
        self._set_summary("sum_sales", f"{_fmt_money(total_sales)} د.ل")
        self._set_summary("sum_profit", f"{_fmt_money(total_profit)} د.ل")
        profit_label = self._summary_rows.get("sum_profit__value")
        if profit_label:
            profit_label.setProperty("loss", total_profit < 0)
            profit_label.style().unpolish(profit_label)
            profit_label.style().polish(profit_label)
        self._set_summary("sum_margin", f"{profit_margin:.2f} %")

    def _set_summary(self, key, value):
        lbl = self._summary_rows.get(key + "__value")
        if lbl:
            lbl.setText(value)

    def _validate(self):
        if not self.current_supplier_id:
            return False, _t("err_supplier", self.language)
        if not self._item_rows:
            return False, _t("err_no_items", self.language)
        for row in self._item_rows:
            if row["product_combo"].current_product_id() is None:
                return False, _t("err_bad_row", self.language)
            if row["qty"].value() <= 0 or row["purchase"].value() <= 0 or row["sale"].value() <= 0:
                return False, _t("err_bad_row", self.language)
            pallet_text = row["pallet_input"].text().strip()
            if pallet_text and pallet_text != "—":
                try:
                    pallet_value = float(pallet_text.replace(",", ""))
                    if pallet_value < 0 or not pallet_value.is_integer():
                        return False, _t("err_bad_row", self.language)
                except ValueError:
                    return False, _t("err_bad_row", self.language)
        return True, ""

    def _pallet_value(self, row):
        pallet_text = row["pallet_input"].text().strip()
        if not pallet_text or pallet_text == "—":
            return None
        return int(float(pallet_text.replace(",", "")))

    def _collect_all(self):
        copied = getattr(self, "_copied_invoice", None)
        return {
            "display_fields": copied.get("display_fields") if copied else None,
            "notes": settings.get("invoice_notes") or "",
            "notes2": settings.get("invoice_notes2") or "",
            "supplier_id": self.current_supplier_id,
            "supplier_invoice_no": self.sup_inv_input.text(),
            "invoice_date": self.date_input.date().toString("yyyy-MM-dd"),
            "items": [
                {
                    "product_id": row["product_combo"].current_product_id(),
                    "quantity": row["qty"].value(),
                    "purchase_usd": row["purchase"].value(),
                    "sale_dzd": row["sale"].value(),
                    "pallet": self._pallet_value(row),
                    "_product_snapshot": row.get("product_snapshot"),
                } for row in self._item_rows
            ],
            "payments": self._collect_amounts(self._amount_rows_payments),
            "discounts": self._collect_amounts(self._amount_rows_discounts),
            "expenses": self._collect_amounts(self._amount_rows_expenses),
        }


    def _on_export_pdf(self):
        valid, error = self._validate()
        if not valid:
            QMessageBox.warning(self, _t("err_title", self.language), error)
            return
        from app.ui.pages.archive import ExportContentDialog
        from app.services.export_service import export_service, DEFAULT_INVOICE_SECTIONS, DEFAULT_INVOICE_ITEM_COLUMNS, DEFAULT_SUPPLIER_FIELDS
        from app.ui.pdf_preview import show_pdf_preview, BACK_TO_OPTIONS
        try:
            dialog = ExportContentDialog(
                self, self.language, self.theme, dict(DEFAULT_INVOICE_SECTIONS),
                list(DEFAULT_INVOICE_ITEM_COLUMNS), list(DEFAULT_SUPPLIER_FIELDS),
            )
            data = self._collect_all()
            calculation = invoice_service._calculate(data["items"], data["payments"], data["discounts"], data["expenses"])
            invoice = asdict(calculation)
            supplier = supplier_service.get_by_id(data["supplier_id"])
            copied = getattr(self, "_copied_invoice", None)
            if copied:
                if copied["supplier_id"] == data["supplier_id"]:
                    supplier = {key: copied.get("supplier_" + key) for key in ("name", "code", "address", "phone", "email")}
                if "_company_snapshot" in copied:
                    invoice["_company_snapshot"] = copied["_company_snapshot"]
            invoice.update({key: value for key, value in data.items() if key != "items"})
            invoice["invoice_no"] = self.inv_no_input.text()
            for key in ("name", "code", "address", "phone", "email"):
                invoice["supplier_" + key] = supplier.get(key) or ""
            enriched_items = []
            for calculated, original in zip(calculation.items, data["items"]):
                product = self._item_rows[len(enriched_items)]["product_info"] or product_service.get_by_id(original["product_id"])
                item = asdict(calculated)
                for key, value in product.items():
                    item["product_" + ("image" if key == "layout_image" else key)] = value
                item["pallet"] = original.get("pallet")
                enriched_items.append(item)
            invoice["items"] = enriched_items
            while dialog.exec() == QDialog.DialogCode.Accepted:
                with TemporaryDirectory(prefix="costprofit-preview-") as directory:
                    filename = f'{invoice["invoice_no"]}.pdf'
                    path = Path(directory) / filename
                    export_service.export_invoice_pdf(
                        invoice, str(path), sections=dialog.get_sections(),
                        columns=dialog.get_columns(), supplier_fields=dialog.get_supplier_fields(),
                    )
                    result = show_pdf_preview(self, path, self.language, filename, allow_options=True)
                if result != BACK_TO_OPTIONS:
                    break
        except Exception as exc:
            QMessageBox.warning(self, _t("err_title", self.language), str(exc))

    def _on_save_draft(self):
        valid, err = self._validate()
        if not valid:
            QMessageBox.warning(self, _t("err_title", self.language), err)
            return
        data = self._collect_all()
        try:
            self.invoice_id = invoice_service.save_draft(self.invoice_id, **data)
            QMessageBox.information(self, _t("saved_msg", self.language),
                                    _t("saved_msg", self.language))
            self._reload_texts()
        except InvoiceError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_archive(self):
        valid, err = self._validate()
        if not valid:
            QMessageBox.warning(self, _t("err_title", self.language), err)
            return
        reply = QMessageBox.question(self, _t("confirm_archive_t", self.language),
            _t("confirm_archive_m", self.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        data = self._collect_all()
        try:
            invoice_service.archive(self.invoice_id, **data)
            QMessageBox.information(self, _t("archived_msg", self.language),
                                    _t("archived_msg", self.language))
            self._on_reset()
        except InvoiceError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_reset(self):
        if self.invoice_id or self._item_rows:
            reply = QMessageBox.question(self, _t("confirm_reset_t", self.language),
                _t("confirm_reset_m", self.language),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.invoice_id = None
        self._reset_form()

    def _reset_form(self):
        self._copied_invoice = None
        self._reload_company_info()
        self.inv_no_input.setText(invoice_service.generate_invoice_number())
        self.sup_inv_input.clear()
        self.date_input.setDate(QDate.currentDate())
        self.current_supplier_id = None
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.setCurrentIndex(0)
        self.supplier_combo.blockSignals(False)
        self._update_supplier_fields(None)
        self._clear_all_items()

        for r in self._amount_rows_payments:
            r.setParent(None); r.deleteLater()
        self._amount_rows_payments.clear()
        self._on_add_payment()

        for r in self._amount_rows_discounts:
            r.setParent(None); r.deleteLater()
        self._amount_rows_discounts.clear()

        for r in self._amount_rows_expenses:
            r.setParent(None); r.deleteLater()
        self._amount_rows_expenses.clear()

        self.tabs.setCurrentIndex(0)
        self._recalculate()

    def _load_invoice(self, invoice_id):
        inv = invoice_service.get_by_id(invoice_id)
        if not inv:
            self._reset_form()
            return
        self._copied_invoice = inv if inv.get("archived_snapshot") or "_company_snapshot" in inv else None
        self._reload_company_info()
        self.inv_no_input.setText(inv["invoice_no"])
        self.sup_inv_input.setText(inv.get("supplier_invoice_no") or "")
        try:
            d = QDate.fromString(inv["invoice_date"], "yyyy-MM-dd")
            if d.isValid():
                self.date_input.setDate(d)
        except Exception:
            pass
        self.current_supplier_id = inv["supplier_id"]
        self._reload_suppliers()
        for i in range(self.supplier_combo.count()):
            if self.supplier_combo.itemData(i) == self.current_supplier_id:
                self.supplier_combo.setCurrentIndex(i); break
        self._update_supplier_fields(self.current_supplier_id)

        self._clear_all_items()
        for item in inv.get("items", []):
            pallet = item.get("pallet")
            if pallet is None:
                pallet = item.get("product_pallet")
            self._add_item_row(
                product_id=item["product_id"],
                qty=item["quantity"],
                purchase=item["purchase_usd"],
                sale=item["sale_dzd"],
                pallet=pallet, product_snapshot=item if self._copied_invoice else None)

        for r in self._amount_rows_payments:
            r.setParent(None); r.deleteLater()
        self._amount_rows_payments.clear()
        for p in inv.get("payments", []):
            row = AmountRow(self, label=p.get("label") or "", amount=p.get("amount", 0))
            self._amount_rows_payments.append(row)
            self.payments_container.addWidget(row)

        for r in self._amount_rows_discounts:
            r.setParent(None); r.deleteLater()
        self._amount_rows_discounts.clear()
        for d in inv.get("discounts", []):
            row = AmountRow(self, label=d.get("label") or "", amount=d.get("amount", 0))
            self._amount_rows_discounts.append(row)
            self.discounts_container.addWidget(row)

        for r in self._amount_rows_expenses:
            r.setParent(None); r.deleteLater()
        self._amount_rows_expenses.clear()
        for e in inv.get("expenses", []):
            row = AmountRow(self, label=e.get("label") or "", amount=e.get("amount", 0))
            self._amount_rows_expenses.append(row)
            self.expenses_container.addWidget(row)

        self._recalculate()

    # ✅ دالة جديدة: يفتح فاتورة موجودة للتعديل من الخارج
    def load_invoice(self, invoice_id: int):
        """يفتح فاتورة موجودة للتعديل (يُستدعى من الخارج)."""
        self.invoice_id = invoice_id
        self._reload_texts()
        self._load_invoice(invoice_id)
        self.tabs.setCurrentIndex(0)

    def reload_language(self, language):
        self.language = language
        self._reload_texts()

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; color: #FFFFFF; }
            QWidget#TabContent { background-color: #000000; }
            QFrame#HeaderCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(37, 99, 235, 0.18), stop:1 rgba(37, 99, 235, 0.02)); border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 14px; margin: 20px 24px 12px 24px; }
            QLabel#PageTitle { color: #FFFFFF; font-size: 24px; font-weight: 700; background: transparent; }
            QLabel#PageSub { color: rgba(148,163,184,0.9); font-size: 14px; background: transparent; }
            QFrame#Card, QFrame#AmountRow { background-color: rgba(15, 29, 53, 0.7); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 12px; }
            QFrame#SummaryCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(15, 29, 53, 0.9), stop:1 rgba(10, 22, 40, 0.95)); border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 14px; }
            QLabel#CardTitle { color: #FFFFFF; font-size: 18px; font-weight: 600; background: transparent; }
            QLabel#FieldLabel { color: rgba(148,163,184,0.95); font-size: 14px; background: transparent; }
            QLabel#TotalValue { color: #60A5FA; font-size: 18px; font-weight: 700; background: transparent; padding-top: 8px; border-top: 1px solid rgba(37, 99, 235, 0.25); }
            QLabel#SummaryLabel { color: rgba(148,163,184,0.95); font-size: 15px; background: transparent; }
            QLabel#SummaryValue { color: #FFFFFF; font-size: 16px; font-weight: 600; background: transparent; }
            QLabel#SummaryProfit { color: #22C55E; font-size: 20px; font-weight: 800; background: transparent; }
            QLabel#SummaryProfit[loss="true"] { color: #EF4444; }
            QLabel#SummaryProfit[loss="false"] { color: #22C55E; }
            QLabel#SummaryCost { color: #60A5FA; font-size: 18px; font-weight: 700; background: transparent; }
            QLineEdit, QTextEdit, QComboBox, QDateEdit { background-color: rgba(15, 29, 53, 0.9); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 8px 12px; font-size: 15px; min-height: 22px; }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border: 1px solid #2563EB; }
            QLineEdit#ReadOnlyInput { background-color: rgba(10, 22, 40, 0.9); color: #A0B8D8; font-weight: 500; font-size: 15px; }
            QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView { background-color: rgba(15, 29, 53, 0.98); color: #FFFFFF; selection-background-color: #2563EB; border: 1px solid rgba(37, 99, 235, 0.5); border-radius: 8px; font-size: 15px; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; padding: 8px 20px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 8px; font-size: 14px; font-weight: 500; padding: 8px 16px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(37, 99, 235, 0.2); border: 1px solid rgba(37, 99, 235, 0.6); }
            QPushButton#RemoveBtn, QPushButton#RemoveRowBtn { background-color: rgba(220, 38, 38, 0.15); color: #F87171; border: 1px solid rgba(220, 38, 38, 0.4); border-radius: 6px; font-size: 15px; padding: 0; }
            QPushButton#RemoveBtn:hover, QPushButton#RemoveRowBtn:hover { background-color: rgba(220, 38, 38, 0.4); color: #FFFFFF; }
            QTabWidget#InvoiceTabs::pane { background-color: #000000; border: none; }
            QTabWidget#InvoiceTabs QTabBar { background-color: rgba(10, 22, 40, 0.95); }
            QTabWidget#InvoiceTabs QTabBar::tab { background-color: transparent; color: rgba(148,163,184,0.85); padding: 14px 26px; margin-right: 4px; border: none; border-bottom: 3px solid transparent; font-size: 15px; font-weight: 500; }
            QTabWidget#InvoiceTabs QTabBar::tab:selected { color: #FFFFFF; border-bottom: 3px solid #2563EB; background-color: rgba(37, 99, 235, 0.1); }
            QTabWidget#InvoiceTabs QTabBar::tab:hover { color: #FFFFFF; background-color: rgba(255,255,255,0.04); }
            QTableWidget { background-color: rgba(15, 29, 53, 0.5); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 12px; gridline-color: transparent; outline: none; font-size: 14px; }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(37, 99, 235, 0.12); }
            QHeaderView::section { background-color: rgba(10, 22, 40, 0.9); color: rgba(148,163,184,0.95); border: none; border-bottom: 1px solid rgba(37, 99, 235, 0.3); padding: 10px 6px; font-weight: 600; font-size: 14px; }
            QFrame#Sep { background-color: rgba(37, 99, 235, 0.2); border: none; }
            QScrollBar:vertical { background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(37, 99, 235, 0.7); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
