"""
صفحة الأرشيف — الفواتير المؤرشفة + المسودات.
"""
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QSize, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QMessageBox,
    QDialog, QScrollArea, QCheckBox, QSizePolicy, QFileDialog,
    QGridLayout,
)

from app.services.invoice_service import invoice_service, InvoiceError
from app.services.supplier_service import supplier_service
from app.services.settings_service import settings
from app.services.product_service import product_service
from app.services.export_service import (safe_filename,
    export_service,
    DEFAULT_INVOICE_SECTIONS,
    INVOICE_ITEM_COLUMNS,
    INVOICE_ITEM_COLUMN_KEYS,
    DEFAULT_INVOICE_ITEM_COLUMNS,
    SUPPLIER_FIELDS,
    SUPPLIER_FIELD_KEYS,
    DEFAULT_SUPPLIER_FIELDS,
)
from app.ui import PageControls
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.pdf_preview import show_pdf_preview, BACK_TO_OPTIONS
from app.ui.theme import set_widget_stylesheet


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "title":         ("Archive",                     "الأرشيف"),
    "subtitle":      ("Search, filter, and manage your invoices.",
                      "ابحث، فلتر، وأدر فواتيرك."),
    "tab_archived":  ("Archived",                    "مؤرشفة"),
    "tab_drafts":    ("Drafts",                      "مسودات"),

    "search_ph":     ("Search by invoice #, supplier inv #, or USD value...",
                      "ابحث برقم الفاتورة، رقم فاتورة المورد، أو قيمة الدولار..."),
    "filter_sup":    ("All Suppliers",               "كل الموردين"),
    "filter_date":   ("All Time",                    "كل الوقت"),
    "filter_custom": ("Custom Range",                "نطاق مخصص"),
    "date_from":     ("From",                        "من"),
    "date_to":       ("To",                          "إلى"),
    "sort_newest":   ("Newest",                      "الأحدث"),
    "sort_oldest":   ("Oldest",                      "الأقدم"),
    "sort_profit_high": ("Highest Profit",           "الأعلى ربحًا"),
    "sort_profit_low":  ("Lowest Profit",            "الأقل ربحًا"),
    "sort_usd_high":    ("Highest USD",              "الأعلى قيمة $"),
    "btn_reset":     ("Reset",                       "إعادة تعيين"),
    "btn_export":    ("📤 Export",                   "📤 تصدير"),

    "count":         ("{n} invoice(s)",              "{n} فاتورة"),

    "col_num":       ("#",                           "#"),
    "col_inv_no":    ("Invoice No.",                 "رقم الفاتورة"),
    "col_supplier":  ("Supplier",                    "المورد"),
    "col_sup_inv":   ("Supplier Inv.",               "فاتورة المورد"),
    "col_items":     ("Total Qty",                   "Total Qty"),
    "col_usd":       ("Total USD",                   "القيمة $"),
    "col_cost":      ("Net Cost (LYD)",              "التكلفة (د.ل)"),
    "col_profit":    ("Profit",                      "الربح"),
    "col_actions":   ("Actions",                     "إجراءات"),

    "no_archived":   ("No archived invoices yet",    "لا توجد فواتير مؤرشفة"),
    "no_drafts":     ("No drafts",                   "لا توجد مسودات"),
    "no_results":    ("No results found",            "لا نتائج"),
    "no_results_sub":("Try different filters.",      "جرّب فلاتر مختلفة."),
    "empty_archived_sub": ("Create and archive your first invoice.",
                           "أنشئ وأرشف أول فاتورة."),
    "empty_drafts_sub":   ("You have no drafts. All your invoices are archived.",
                           "ليس لديك مسودات. كل فواتيرك مؤرشفة."),

    "details_title": ("Invoice Details",             "تفاصيل الفاتورة"),
    "sec_info":      ("Invoice Info",                "بيانات الفاتورة"),
    "sec_items":     ("Products",                    "الأصناف"),
    "sec_payments":  ("Payments",                    "الدفعات"),
    "sec_discounts": ("Discounts",                   "الخصومات"),
    "sec_expenses":  ("Additional Expenses",         "المصاريف الإضافية"),
    "sec_summary":   ("Summary",                     "الملخص"),
    "btn_close":     ("Close",                       "إغلاق"),

    "lbl_inv_no":    ("Invoice No.",                 "رقم الفاتورة"),
    "lbl_sup_inv":   ("Supplier Inv.",               "فاتورة المورد"),
    "lbl_date":      ("Date",                        "التاريخ"),
    "lbl_supplier":  ("Supplier",                    "المورد"),
    "lbl_qty":       ("Qty",                         "Qty"),
    "lbl_purchase":  ("Price $",                  "الشراء $"),
    "lbl_unit":      ("Unit LYD",                    "الوحدة د.ل"),
    "lbl_sale":      ("Sale LYD",                    "البيع د.ل"),
    "lbl_total":     ("Total $",                     "الإجمالي $"),
    "lbl_profit":    ("Profit",                      "الربح"),
    "lbl_product":   ("Product",                     "Product"),

    "sum_payments":  ("Total Payments",              "إجمالي الدفعات"),
    "sum_discounts": ("Total Discounts",             "إجمالي الخصومات"),
    "sum_net":       ("Net Payments",                "صافي المدفوعات"),
    "sum_expenses":  ("Total Expenses",              "إجمالي المصاريف"),
    "sum_cost":      ("Net Cost (LYD)",              "صافي التكلفة (د.ل)"),
    "sum_usd":       ("Total Value (USD)",           "القيمة بالدولار"),
    "sum_rate":      ("Exchange Rate",               "سعر الصرف"),
    "sum_sales":     ("Total Sales (LYD)",           "إجمالي البيع (د.ل)"),
    "sum_profit":    ("Total Profit (LYD)",          "إجمالي الربح (د.ل)"),
    "sum_margin":    ("Profit Margin",               "هامش الربح"),

    "confirm_delete_t": ("Delete Invoice",           "حذف الفاتورة"),
    "confirm_delete_m": ("Are you sure you want to permanently delete invoice {inv}?\nThis cannot be undone.",
                         "هل تريد حذف الفاتورة {inv} نهائيًا؟\nلا يمكن التراجع."),
    "understand":    ("I understand this action is permanent",
                      "أفهم أن هذا الإجراء نهائي"),
    "btn_delete":    ("Delete",                      "حذف"),
    "btn_cancel":    ("Cancel",                      "إلغاء"),

    "err_title":     ("Error",                       "خطأ"),
    "info_title":    ("Information",                 "معلومة"),
    "err_delete":    ("Cannot delete invoice.",      "لا يمكن حذف الفاتورة."),

    "pdf_save_title":   ("Save Invoice PDF",         "حفظ فاتورة PDF"),
    "pdf_saved":        ("PDF saved successfully:\n{path}",
                         "تم حفظ PDF بنجاح:\n{path}"),
    "pdf_err":          ("Failed to export PDF:\n{err}",
                         "فشل تصدير PDF:\n{err}"),
    "excel_save_title": ("Save Invoice Excel",       "حفظ فاتورة Excel"),
    "excel_saved":      ("Excel saved successfully:\n{path}",
                         "تم حفظ Excel بنجاح:\n{path}"),
    "excel_err":        ("Failed to export Excel:\n{err}",
                         "فشل تصدير Excel:\n{err}"),
    "inv_not_found":    ("Invoice not found.",       "الفاتورة غير موجودة."),

    "select_content_title": ("Select Content to Export",
                             "اختر المحتوى للتصدير"),
    "select_content_sub":   ("Choose sections, columns, and supplier fields:",
                             "اختر الأقسام والأعمدة وحقول المورد:"),
    "sections_title":       ("Sections",             "الأقسام"),
    "supplier_fields_title":("Supplier Data Fields",  "حقول بيانات المورد"),
    "sec_header":   ("Company Header",               "ترويسة الشركة"),
    "sec_info":     ("Invoice Info",                 "بيانات الفاتورة"),
    "sec_items":    ("Products Table",               "جدول الأصناف"),
    "sec_payments": ("Payments",                     "الدفعات"),
    "sec_discounts":("Discounts",                    "الخصومات"),
    "sec_expenses": ("Additional Expenses",          "المصاريف الإضافية"),
    "sec_summary":  ("Summary",                      "الملخص"),
    "sec_marks": ("Stamp and Signature", "الختم والتوقيع"),
    "sec_footer":   ("Notes",                        "الملاحظات"),
    "select_all":   ("Select All",                   "تحديد الكل"),
    "deselect_all": ("Deselect All",                 "إلغاء الكل"),
    "save_default": ("Save as Default",              "حفظ كافتراضي"),
    "btn_export_pdf": ("Export PDF",                 "تصدير PDF"),
    "default_saved":  ("Default settings saved.",    "تم حفظ الإعدادات كافتراضية."),
    "no_section_selected": ("Please select at least one section.",
                            "الرجاء اختيار قسم واحد على الأقل."),
    "columns_title":    ("Columns of Products Table",
                         "أعمدة جدول الأصناف"),
    "product_required": ("Product column is required.",
                         "عمود الصنف إلزامي."),
    # Duplicate
    "duplicate_done":   ("Invoice duplicated as a new draft.",
                         "تم نسخ الفاتورة كمسودة جديدة."),
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
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


# ============================================================
# نافذة اختيار محتوى التصدير
# ============================================================
class ExportContentDialog(QDialog):
    """نافذة اختيار الأقسام والأعمدة وحقول المورد قبل التصدير."""

    SECTION_KEYS = [
        ("header",   "sec_header"),
        ("info",     "sec_info"),
        ("items",    "sec_items"),
        ("payments", "sec_payments"),
        ("discounts","sec_discounts"),
        ("expenses", "sec_expenses"),
        ("summary",  "sec_summary"),
        ("footer",   "sec_footer"),
        ("marks",    "sec_marks"),
    ]

    def __init__(self, parent, language, theme,
                 sections: dict, columns: list[str],
                 supplier_fields: list[str]):
        super().__init__(parent)
        self.language = language
        self.palette_data = get_palette(theme)
        self.sections = dict(sections)
        self.columns = list(columns)
        self.supplier_fields = list(supplier_fields)
        self.checkboxes = {}
        self.col_checkboxes = {}
        self.sup_checkboxes = {}

        self.setWindowTitle(_t("select_content_title", language))
        self.setModal(True)
        self.setMinimumWidth(720)
        self.setMinimumHeight(650)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("DialogContent")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

        title = QLabel(_t("select_content_title", self.language))
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        sub = QLabel(_t("select_content_sub", self.language))
        sub.setObjectName("DialogSub")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        sep = QFrame(); sep.setFixedHeight(1); sep.setObjectName("Sep")
        layout.addWidget(sep)

        sec_lbl = QLabel(_t("sections_title", self.language))
        sec_lbl.setObjectName("SectionLabel")
        layout.addWidget(sec_lbl)

        grid = QGridLayout(); grid.setSpacing(6)
        for i, (key, text_key) in enumerate(self.SECTION_KEYS):
            cb = QCheckBox(_t(text_key, self.language))
            cb.setChecked(self.sections.get(key, True))
            self.checkboxes[key] = cb
            grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(grid)

        tools = QHBoxLayout(); tools.setSpacing(8)
        sa = QPushButton(_t("select_all", self.language))
        sa.setObjectName("SmallBtn")
        sa.setCursor(Qt.CursorShape.PointingHandCursor)
        sa.setMinimumHeight(30)
        sa.clicked.connect(lambda: self._set_all_sections(True))
        tools.addWidget(sa)
        da = QPushButton(_t("deselect_all", self.language))
        da.setObjectName("SmallBtn")
        da.setCursor(Qt.CursorShape.PointingHandCursor)
        da.setMinimumHeight(30)
        da.clicked.connect(lambda: self._set_all_sections(False))
        tools.addWidget(da)
        tools.addStretch()
        layout.addLayout(tools)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setObjectName("Sep")
        layout.addWidget(sep2)

        sup_lbl = QLabel(_t("supplier_fields_title", self.language))
        sup_lbl.setObjectName("SectionLabel")
        layout.addWidget(sup_lbl)

        sup_grid = QGridLayout(); sup_grid.setSpacing(6)
        for i, (key, lbl_en, lbl_ar, _d) in enumerate(SUPPLIER_FIELDS):
            cb = QCheckBox(lbl_ar if self.language == "ar" else lbl_en)
            cb.setChecked(key in self.supplier_fields)
            self.sup_checkboxes[key] = cb
            sup_grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(sup_grid)

        sup_tools = QHBoxLayout(); sup_tools.setSpacing(8)
        ssa = QPushButton(_t("select_all", self.language))
        ssa.setObjectName("SmallBtn")
        ssa.setCursor(Qt.CursorShape.PointingHandCursor)
        ssa.setMinimumHeight(30)
        ssa.clicked.connect(lambda: self._set_all_supplier(True))
        sup_tools.addWidget(ssa)
        sda = QPushButton(_t("deselect_all", self.language))
        sda.setObjectName("SmallBtn")
        sda.setCursor(Qt.CursorShape.PointingHandCursor)
        sda.setMinimumHeight(30)
        sda.clicked.connect(lambda: self._set_all_supplier(False))
        sup_tools.addWidget(sda)
        sup_tools.addStretch()
        layout.addLayout(sup_tools)

        sep3 = QFrame(); sep3.setFixedHeight(1); sep3.setObjectName("Sep")
        layout.addWidget(sep3)

        cols_lbl = QLabel(_t("columns_title", self.language))
        cols_lbl.setObjectName("SectionLabel")
        layout.addWidget(cols_lbl)

        cols_grid = QGridLayout(); cols_grid.setSpacing(6)
        for i, (key, lbl_en, lbl_ar, _d) in enumerate(INVOICE_ITEM_COLUMNS):
            cb = QCheckBox(lbl_ar if self.language == "ar" else lbl_en)
            cb.setChecked(key in self.columns)
            if key == "product_name":
                cb.setEnabled(False)
                cb.setToolTip(_t("product_required", self.language))
            self.col_checkboxes[key] = cb
            cols_grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(cols_grid)

        col_tools = QHBoxLayout(); col_tools.setSpacing(8)
        csa = QPushButton(_t("select_all", self.language))
        csa.setObjectName("SmallBtn")
        csa.setCursor(Qt.CursorShape.PointingHandCursor)
        csa.setMinimumHeight(30)
        csa.clicked.connect(lambda: self._set_all_columns(True))
        col_tools.addWidget(csa)
        cda = QPushButton(_t("deselect_all", self.language))
        cda.setObjectName("SmallBtn")
        cda.setCursor(Qt.CursorShape.PointingHandCursor)
        cda.setMinimumHeight(30)
        cda.clicked.connect(lambda: self._set_all_columns(False))
        col_tools.addWidget(cda)
        col_tools.addStretch()
        layout.addLayout(col_tools)

        footer = QFrame()
        footer.setObjectName("Footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(28, 14, 28, 16)
        footer_layout.setSpacing(8)

        self.save_default_btn = QPushButton(_t("save_default", self.language))
        self.save_default_btn.setObjectName("SecondaryBtn")
        self.save_default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_default_btn.setMinimumHeight(40)
        self.save_default_btn.clicked.connect(self._on_save_default)
        footer_layout.addWidget(self.save_default_btn)

        footer_layout.addStretch()

        cancel_btn = QPushButton(_t("btn_cancel", self.language))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        export_btn = QPushButton(_t("btn_export_pdf", self.language))
        export_btn.setObjectName("PrimaryBtn")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setMinimumHeight(40)
        export_btn.setMinimumWidth(140)
        export_btn.clicked.connect(self._on_export)
        footer_layout.addWidget(export_btn)

        outer.addWidget(footer)

    def _set_all_sections(self, value):
        for cb in self.checkboxes.values():
            cb.setChecked(value)

    def _set_all_supplier(self, value):
        for cb in self.sup_checkboxes.values():
            cb.setChecked(value)

    def _set_all_columns(self, value):
        for key, cb in self.col_checkboxes.items():
            cb.setChecked(True if key == "product_name" else value)

    def _on_save_default(self):
        try:
            settings.set("invoice_pdf_default_sections",
                         json.dumps({k: cb.isChecked() for k, cb in self.checkboxes.items()}))
            settings.set("invoice_pdf_default_supplier_fields",
                         json.dumps([k for k, cb in self.sup_checkboxes.items() if cb.isChecked()]))
            cols = [k for k, cb in self.col_checkboxes.items() if cb.isChecked()]
            if "product_name" not in cols:
                cols.insert(0, "product_name")
            settings.set("invoice_pdf_default_columns", json.dumps(cols))
        except Exception:
            pass
        QMessageBox.information(self, _t("info_title", self.language),
                                _t("default_saved", self.language))

    def _on_export(self):
        if not any(cb.isChecked() for cb in self.checkboxes.values()):
            QMessageBox.warning(self, _t("err_title", self.language),
                                _t("no_section_selected", self.language))
            return
        self.col_checkboxes["product_name"].setChecked(True)
        self.accept()

    def get_sections(self):
        return {k: cb.isChecked() for k, cb in self.checkboxes.items()}

    def get_columns(self):
        cols = [k for k, cb in self.col_checkboxes.items() if cb.isChecked()]
        if "product_name" not in cols:
            cols.insert(0, "product_name")
        return [k for k in INVOICE_ITEM_COLUMN_KEYS if k in cols]

    def get_supplier_fields(self):
        return [k for k, cb in self.sup_checkboxes.items() if cb.isChecked()]

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QWidget#DialogContent { background-color: #0A1220; }
            QFrame#Footer { background-color: #0A1220; border-top: 1px solid rgba(37, 99, 235, 0.2); }
            QLabel#DialogTitle { color: #FFFFFF; font-size: 18px; font-weight: 700; background: transparent; }
            QLabel#DialogSub { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#SectionLabel { color: #60A5FA; font-size: 13px; font-weight: 600; background: transparent; padding-top: 4px; }
            QFrame#Sep { background-color: rgba(37, 99, 235, 0.25); border: none; }
            QCheckBox { color: #FFFFFF; font-size: 13px; spacing: 8px; padding: 6px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(37, 99, 235, 0.5); background-color: rgba(15, 29, 53, 0.9); }
            QCheckBox::indicator:checked { background-color: #2563EB; border: 1px solid #2563EB; }
            QCheckBox:disabled { color: rgba(148,163,184,0.5); }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 16px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(37, 99, 235, 0.2); border: 1px solid rgba(37, 99, 235, 0.6); }
            QPushButton#SmallBtn { background-color: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 6px; font-size: 12px; font-weight: 500; padding: 5px 12px; }
            QPushButton#SmallBtn:hover { background-color: rgba(37, 99, 235, 0.35); color: #FFFFFF; }
            QScrollBar:vertical { background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)


# ============================================================
# نافذة تفاصيل الفاتورة
# ============================================================
def _load_default_sections() -> dict:
    try:
        raw = settings.get("invoice_pdf_default_sections", "")
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                result = dict(DEFAULT_INVOICE_SECTIONS)
                result.update({k: bool(v) for k, v in data.items()
                               if k in DEFAULT_INVOICE_SECTIONS})
                return result
    except Exception:
        pass
    return dict(DEFAULT_INVOICE_SECTIONS)

def _load_default_columns() -> list[str]:
    try:
        raw = settings.get("invoice_pdf_default_columns", "")
        if raw:
            data = json.loads(raw)
            if isinstance(data, list):
                cols = [k for k in data if k in INVOICE_ITEM_COLUMN_KEYS]
                if "product_name" not in cols:
                    cols.insert(0, "product_name")
                return cols
    except Exception:
        pass
    return list(DEFAULT_INVOICE_ITEM_COLUMNS)

def _load_default_supplier_fields() -> list[str]:
    try:
        raw = settings.get("invoice_pdf_default_supplier_fields", "")
        if raw:
            data = json.loads(raw)
            if isinstance(data, list):
                return [k for k in data if k in SUPPLIER_FIELD_KEYS]
    except Exception:
        pass
    return list(DEFAULT_SUPPLIER_FIELDS)


def _preview_invoice_pdf(parent, full, language, theme):
    sections = _load_default_sections()
    columns = _load_default_columns()
    supplier_fields = _load_default_supplier_fields()
    dlg = ExportContentDialog(
        parent, language, theme,
        sections, columns, supplier_fields,
    )
    default_name = f"{safe_filename(full['invoice_no'])}_{date.today().isoformat()}.pdf"
    while dlg.exec() == QDialog.DialogCode.Accepted:
        try:
            with TemporaryDirectory(prefix="costprofit-preview-") as temp_dir:
                file_path = Path(temp_dir) / default_name
                export_service.export_invoice_pdf(
                    full, str(file_path), sections=dlg.get_sections(),
                    columns=dlg.get_columns(), supplier_fields=dlg.get_supplier_fields(),
                )
                result = show_pdf_preview(parent, file_path, language, default_name, allow_options=True)
            if result != BACK_TO_OPTIONS:
                return
        except Exception as e:
            QMessageBox.warning(parent, _t("err_title", language), _t("pdf_err", language, err=str(e)))
            return


class InvoiceDetailsDialog(QDialog):

    def __init__(self, parent, language, theme, invoice_data):
        super().__init__(parent)
        self.language = language
        self.theme = theme
        self.palette_data = get_palette(theme)
        self.inv = invoice_data
        self.setWindowTitle(_t("details_title", language))
        self.setMinimumWidth(950)
        self.setMinimumHeight(650)
        self.setModal(True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        inv = self.inv
        L = self.language
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("HeaderCard")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 20)

        text_col = QVBoxLayout(); text_col.setSpacing(4)
        title = QLabel(inv["invoice_no"])
        title.setObjectName("DialogTitle")
        text_col.addWidget(title)

        sup_lbl = QLabel(f"🏢  {inv.get('supplier_name', '—')}   •   {inv.get('invoice_date', '')}")
        sup_lbl.setObjectName("DialogSub")
        text_col.addWidget(sup_lbl)
        hl.addLayout(text_col)
        hl.addStretch()

        is_archived = (inv.get("status") == "archived")
        status_badge = QLabel(_t("tab_archived", L) if is_archived else _t("tab_drafts", L))
        status_badge.setObjectName("StatusBadgeArchived" if is_archived else "StatusBadgeDraft")
        hl.addWidget(status_badge)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("DetailsContent")
        scroll.setWidget(content)

        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 20, 28, 20)
        cl.setSpacing(16)

        info_card = QFrame(); info_card.setObjectName("Card")
        il = QHBoxLayout(info_card)
        il.setContentsMargins(20, 14, 20, 14); il.setSpacing(24)

        for label, value in [
            (_t("lbl_inv_no", L), inv["invoice_no"]),
            (_t("lbl_sup_inv", L), inv.get("supplier_invoice_no") or "—"),
            (_t("lbl_date", L), inv.get("invoice_date", "—")),
            (_t("lbl_supplier", L), inv.get("supplier_name", "—")),
        ]:
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(label); lbl.setObjectName("InfoLabel")
            col.addWidget(lbl)
            val = QLabel(value); val.setObjectName("InfoValue")
            col.addWidget(val)
            il.addLayout(col)

        il.addStretch()
        cl.addWidget(info_card)

        items_lbl = QLabel(_t("sec_items", L))
        items_lbl.setObjectName("SectionLabel")
        cl.addWidget(items_lbl)

        items_table = QTableWidget()
        items_table.setColumnCount(7)
        items_table.setRowCount(len(inv.get("items", [])))
        items_table.verticalHeader().setVisible(False)
        items_table.setShowGrid(False)
        items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        items_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        items_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        items_table.verticalHeader().setDefaultSectionSize(40)
        items_table.setMinimumHeight(180)

        headers = [
            _t("lbl_product", L), _t("lbl_qty", L), _t("lbl_purchase", L),
            _t("lbl_unit", L), _t("lbl_sale", L), _t("lbl_total", L),
            _t("lbl_profit", L),
        ]
        items_table.setHorizontalHeaderLabels(headers)

        for i, item in enumerate(inv.get("items", [])):
            items_table.setItem(i, 0, QTableWidgetItem(item.get("product_name", "—") + (" — " + item["product_pattern"] if item.get("product_pattern") else "")))
            items_table.setItem(i, 1, QTableWidgetItem(_fmt_num(item.get("quantity"))))
            items_table.setItem(i, 2, QTableWidgetItem(_fmt_money(item.get("purchase_usd"))))
            items_table.setItem(i, 3, QTableWidgetItem(_fmt_money(item.get("purchase_dzd"))))
            items_table.setItem(i, 4, QTableWidgetItem(_fmt_money(item.get("sale_dzd"))))
            items_table.setItem(i, 5, QTableWidgetItem(_fmt_money(item.get("total_usd"))))
            items_table.setItem(i, 6, QTableWidgetItem(_fmt_money(item.get("total_profit"))))

        h = items_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        cl.addWidget(items_table)
        for key in ("notes", "notes2"):
            if inv.get(key):
                text = QLabel(inv[key])
                text.setWordWrap(True)
                text.setTextFormat(Qt.TextFormat.PlainText)
                cl.addWidget(text)


        pd_row = QHBoxLayout(); pd_row.setSpacing(16)

        pay_card = QFrame(); pay_card.setObjectName("Card")
        pl = QVBoxLayout(pay_card); pl.setContentsMargins(20, 14, 20, 14); pl.setSpacing(8)
        pt = QLabel(_t("sec_payments", L)); pt.setObjectName("CardTitle")
        pl.addWidget(pt)
        payments = inv.get("payments", [])
        if payments:
            for p in payments:
                row = QHBoxLayout()
                lbl = QLabel(p.get("label") or "—"); lbl.setObjectName("MiniLabel")
                row.addWidget(lbl); row.addStretch()
                val = QLabel(f"{_fmt_money(p.get('amount'))} د.ل")
                val.setObjectName("MiniValue")
                row.addWidget(val)
                pl.addLayout(row)
        else:
            empty = QLabel("—"); empty.setObjectName("MiniLabel")
            pl.addWidget(empty)
        pl.addStretch()
        pd_row.addWidget(pay_card, 1)

        dis_card = QFrame(); dis_card.setObjectName("Card")
        dl = QVBoxLayout(dis_card); dl.setContentsMargins(20, 14, 20, 14); dl.setSpacing(8)
        dt = QLabel(_t("sec_discounts", L)); dt.setObjectName("CardTitle")
        dl.addWidget(dt)
        discounts = inv.get("discounts", [])
        if discounts:
            for d in discounts:
                row = QHBoxLayout()
                lbl = QLabel(d.get("label") or "—"); lbl.setObjectName("MiniLabel")
                row.addWidget(lbl); row.addStretch()
                val = QLabel(f"- {_fmt_money(d.get('amount'))} د.ل")
                val.setObjectName("MiniValueRed")
                row.addWidget(val)
                dl.addLayout(row)
        else:
            empty = QLabel("—"); empty.setObjectName("MiniLabel")
            dl.addWidget(empty)
        dl.addStretch()
        pd_row.addWidget(dis_card, 1)

        exp_card = QFrame(); exp_card.setObjectName("Card")
        el = QVBoxLayout(exp_card); el.setContentsMargins(20, 14, 20, 14); el.setSpacing(8)
        et = QLabel(_t("sec_expenses", L)); et.setObjectName("CardTitle")
        el.addWidget(et)
        expenses = inv.get("expenses", [])
        if expenses:
            for e in expenses:
                row = QHBoxLayout()
                lbl = QLabel(e.get("label") or "—"); lbl.setObjectName("MiniLabel")
                row.addWidget(lbl); row.addStretch()
                val = QLabel(f"{_fmt_money(e.get('amount'))} د.ل")
                val.setObjectName("MiniValue")
                row.addWidget(val)
                el.addLayout(row)
        else:
            empty = QLabel("—"); empty.setObjectName("MiniLabel")
            el.addWidget(empty)
        el.addStretch()
        pd_row.addWidget(exp_card, 1)

        cl.addLayout(pd_row)

        sum_card = QFrame(); sum_card.setObjectName("SummaryCard")
        sl = QVBoxLayout(sum_card); sl.setContentsMargins(24, 18, 24, 18); sl.setSpacing(8)
        st = QLabel(_t("sec_summary", L)); st.setObjectName("CardTitle")
        sl.addWidget(st)
        sl.addSpacing(4)

        for key, value, color_style in [
            ("sum_payments", f"{_fmt_money(inv.get('total_payments'))} د.ل", ""),
            ("sum_discounts", f"- {_fmt_money(inv.get('total_discounts'))} د.ل", ""),
            ("sum_net", f"{_fmt_money(inv.get('net_payments'))} د.ل", ""),
            ("sum_expenses", f"+ {_fmt_money(inv.get('total_expenses'))} د.ل", ""),
            ("sum_cost", f"{_fmt_money(inv.get('net_cost'))} د.ل", "cost"),
            ("sum_usd", f"$ {_fmt_money(inv.get('total_usd'))}", ""),
            ("sum_rate", f"{inv.get('exchange_rate', 0):.4f}", ""),
            ("sum_sales", f"{_fmt_money(inv.get('total_sales'))} د.ل", ""),
            ("sum_profit", f"{_fmt_money(inv.get('total_profit'))} د.ل", "profit"),
            ("sum_margin", f"{inv.get('profit_margin', 0):.2f} %", ""),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(_t(key, L)); lbl.setObjectName("SummaryLabel")
            row.addWidget(lbl); row.addStretch()
            val = QLabel(value)
            val.setObjectName("SummaryProfit" if color_style == "profit"
                             else "SummaryCost" if color_style == "cost"
                             else "SummaryValue")
            row.addWidget(val)
            sl.addLayout(row)

        cl.addWidget(sum_card)
        cl.addStretch()

        footer = QFrame(); footer.setObjectName("Footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 14, 28, 16)
        self.pdf_btn = QPushButton(_t("btn_export_pdf", L))
        self.pdf_btn.setObjectName("PrimaryBtn")
        self.pdf_btn.setMinimumHeight(40)
        self.pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pdf_btn.clicked.connect(self._on_pdf)
        fl.addWidget(self.pdf_btn)
        fl.addStretch()
        close_btn = QPushButton(_t("btn_close", L))
        close_btn.setObjectName("PrimaryBtn")
        close_btn.setMinimumHeight(40); close_btn.setMinimumWidth(120)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        fl.addWidget(close_btn)
        outer.addWidget(footer)

    def _on_pdf(self):
        _preview_invoice_pdf(self, self.inv, self.language, self.theme)

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QWidget#DetailsContent { background-color: #0A1220; }
            QFrame#HeaderCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(37, 99, 235, 0.2), stop:1 rgba(37, 99, 235, 0.02)); border-bottom: 1px solid rgba(37, 99, 235, 0.3); }
            QFrame#Footer { background-color: #0A1220; border-top: 1px solid rgba(37, 99, 235, 0.2); }
            QLabel#DialogTitle { color: #FFFFFF; font-size: 22px; font-weight: 700; background: transparent; }
            QLabel#DialogSub { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#SectionLabel { color: #60A5FA; font-size: 15px; font-weight: 600; background: transparent; }
            QLabel#CardTitle { color: #FFFFFF; font-size: 15px; font-weight: 600; background: transparent; }
            QLabel#InfoLabel { color: rgba(148,163,184,0.75); font-size: 11px; background: transparent; }
            QLabel#InfoValue { color: #FFFFFF; font-size: 14px; font-weight: 600; background: transparent; }
            QLabel#MiniLabel { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#MiniValue { color: #FFFFFF; font-size: 13px; font-weight: 600; background: transparent; }
            QLabel#MiniValueRed { color: #F87171; font-size: 13px; font-weight: 600; background: transparent; }
            QLabel#SummaryLabel { color: rgba(148,163,184,0.95); font-size: 14px; background: transparent; }
            QLabel#SummaryValue { color: #FFFFFF; font-size: 14px; font-weight: 600; background: transparent; }
            QLabel#SummaryProfit { color: #22C55E; font-size: 16px; font-weight: 700; background: transparent; }
            QLabel#SummaryCost { color: #60A5FA; font-size: 15px; font-weight: 700; background: transparent; }
            QLabel { color: #FFFFFF; background: transparent; font-size: 13px; }
            QLabel#StatusBadgeArchived { background-color: rgba(34,197,94,0.15); color: #22C55E; border: 1px solid rgba(34,197,94,0.5); border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 13px; }
            QLabel#StatusBadgeDraft { background-color: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.5); border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 13px; }
            QFrame#Card { background-color: rgba(15, 29, 53, 0.7); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 10px; }
            QFrame#SummaryCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(15, 29, 53, 0.9), stop:1 rgba(10, 22, 40, 0.95)); border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 12px; }
            QTableWidget { background-color: rgba(15, 29, 53, 0.5); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 10px; gridline-color: transparent; outline: none; font-size: 13px; }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(37, 99, 235, 0.12); }
            QHeaderView::section { background-color: rgba(10, 22, 40, 0.9); color: rgba(148,163,184,0.9); border: none; border-bottom: 1px solid rgba(37, 99, 235, 0.3); padding: 8px 6px; font-weight: 600; font-size: 12px; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QScrollBar:vertical { background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)


# ============================================================
# نافذة تأكيد الحذف
# ============================================================
class DeleteConfirmDialog(QDialog):

    def __init__(self, parent, language, invoice_no):
        super().__init__(parent)
        self.language = language
        self.invoice_no = invoice_no
        self.setWindowTitle(_t("confirm_delete_t", language))
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        icon = QLabel("⚠")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_widget_stylesheet(icon, "font-size: 48px; color: #DC2626;")
        layout.addWidget(icon)

        title = QLabel(_t("confirm_delete_t", self.language))
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(_t("confirm_delete_m", self.language, inv=self.invoice_no))
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setObjectName("DialogSub")
        layout.addWidget(msg)

        self.understand_cb = QCheckBox(_t("understand", self.language))
        self.understand_cb.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.understand_cb)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton(_t("btn_cancel", self.language))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setMinimumHeight(40); cancel_btn.setMinimumWidth(110)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.delete_btn = QPushButton(_t("btn_delete", self.language))
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.setMinimumHeight(40); self.delete_btn.setMinimumWidth(140)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

    def _on_state_changed(self, state):
        self.delete_btn.setEnabled(state == Qt.CheckState.Checked.value)

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QLabel#DialogTitle { color: #DC2626; font-size: 20px; font-weight: 700; background: transparent; }
            QLabel#DialogSub { color: rgba(203,213,225,0.9); font-size: 14px; background: transparent; }
            QCheckBox { color: #FFFFFF; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(37, 99, 235, 0.5); background-color: rgba(15, 29, 53, 0.9); }
            QCheckBox::indicator:checked { background-color: #DC2626; border: 1px solid #DC2626; }
            QPushButton#DangerBtn { background-color: #DC2626; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#DangerBtn:hover { background-color: #EF4444; }
            QPushButton#DangerBtn:disabled { background-color: rgba(220,38,38,0.3); color: rgba(255,255,255,0.5); }
            QPushButton#SecondaryBtn { background-color: transparent; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(255,255,255,0.06); }
        """)


# ============================================================
# الصفحة الرئيسية
# ============================================================
class ArchivePage(QWidget):

    edit_draft_requested = Signal(int)

    ACTIONS_COL_WIDTH = 210

    def __init__(self, theme="dark", language="en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.current_status = "archived"
        self.date_filter_mode = "all"
        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header_card = QFrame(); header_card.setObjectName("HeaderCard")
        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(24, 18, 24, 18)

        text_col = QVBoxLayout(); text_col.setSpacing(4)
        self.title = QLabel(""); self.title.setObjectName("PageTitle")
        text_col.addWidget(self.title)
        self.subtitle = QLabel(""); self.subtitle.setObjectName("PageSub")
        text_col.addWidget(self.subtitle)
        hl.addLayout(text_col); hl.addStretch()

        self.export_btn = QPushButton("")
        self.export_btn.setObjectName("SecondaryBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setMinimumHeight(42)
        self.export_btn.clicked.connect(self._on_export_list)
        hl.addWidget(self.export_btn)
        layout.addWidget(header_card)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("ArchiveTabs")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.archived_tab = QWidget()
        self._build_table_tab(self.archived_tab, is_draft=False)
        self.tabs.addTab(self.archived_tab, "")

        self.drafts_tab = QWidget()
        self._build_table_tab(self.drafts_tab, is_draft=True)
        self.tabs.addTab(self.drafts_tab, "")

        layout.addWidget(self.tabs, 1)

    def _build_table_tab(self, tab, is_draft):
        prefix = "d_" if is_draft else ""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        toolbar1 = QHBoxLayout(); toolbar1.setSpacing(10)
        search_input = QLineEdit()
        search_input.setMinimumHeight(40)
        search_input.textChanged.connect(self.refresh)
        setattr(self, f"{prefix}search_input", search_input)
        toolbar1.addWidget(search_input, 3)

        if not is_draft:
            sup_filter = QComboBox()
            sup_filter.setMinimumHeight(40); sup_filter.setMinimumWidth(180)
            sup_filter.currentIndexChanged.connect(self.refresh)
            setattr(self, "sup_filter", sup_filter)
            toolbar1.addWidget(sup_filter, 1)

        sort_combo = QComboBox()
        sort_combo.setMinimumHeight(40); sort_combo.setMinimumWidth(150)
        sort_combo.currentIndexChanged.connect(self.refresh)
        setattr(self, f"{prefix}sort_combo", sort_combo)
        toolbar1.addWidget(sort_combo)
        layout.addLayout(toolbar1)

        if not is_draft:
            toolbar2 = QHBoxLayout(); toolbar2.setSpacing(10)
            self.date_combo = QComboBox()
            self.date_combo.setMinimumHeight(40); self.date_combo.setMinimumWidth(150)
            self.date_combo.currentIndexChanged.connect(self._on_date_filter_changed)
            toolbar2.addWidget(self.date_combo)

            self.from_lbl = QLabel(""); self.from_lbl.setObjectName("Muted")
            toolbar2.addWidget(self.from_lbl)
            self.from_date = QDateEdit()
            self.from_date.setCalendarPopup(True)
            self.from_date.setDate(QDate.currentDate().addMonths(-1))
            self.from_date.setDisplayFormat("yyyy-MM-dd")
            self.from_date.setMinimumHeight(40)
            self.from_date.dateChanged.connect(self.refresh)
            self.from_date.setVisible(False)
            toolbar2.addWidget(self.from_date)

            self.to_lbl = QLabel(""); self.to_lbl.setObjectName("Muted")
            toolbar2.addWidget(self.to_lbl)
            self.to_date = QDateEdit()
            self.to_date.setCalendarPopup(True)
            self.to_date.setDate(QDate.currentDate())
            self.to_date.setDisplayFormat("yyyy-MM-dd")
            self.to_date.setMinimumHeight(40)
            self.to_date.dateChanged.connect(self.refresh)
            self.to_date.setVisible(False)
            toolbar2.addWidget(self.to_date)

            toolbar2.addStretch()

            self.reset_btn = QPushButton("")
            self.reset_btn.setObjectName("SecondaryBtn")
            self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reset_btn.setMinimumHeight(40)
            self.reset_btn.clicked.connect(self._reset_filters)
            toolbar2.addWidget(self.reset_btn)
            layout.addLayout(toolbar2)

        counter = QLabel(""); counter.setObjectName("CounterLabel")
        setattr(self, f"{prefix}counter", counter)
        layout.addWidget(counter)

        table = QTableWidget()
        table.setColumnCount(9)
        table.setRowCount(0)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.verticalHeader().setDefaultSectionSize(62)
        table.itemDoubleClicked.connect(self._on_row_double_clicked)
        setattr(self, f"{prefix}table", table)
        pager = PageControls(self.refresh, self)
        setattr(self, f"{prefix}pager", pager)
        layout.addWidget(pager)
        layout.addWidget(table, 1)

        empty_box = QFrame(); empty_box.setObjectName("EmptyBox")
        el = QVBoxLayout(empty_box)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter); el.setSpacing(10)
        setattr(self, f"{prefix}empty_box", empty_box)

        icon = QLabel()
        icon.setPixmap(make_icon("archive" if not is_draft else "invoice",
                                 color="#2563EB" if not is_draft else "#F59E0B",
                                 size=72).pixmap(72, 72))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(icon)

        et = QLabel(""); et.setObjectName("EmptyTitle")
        et.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(et)
        setattr(self, f"{prefix}empty_title", et)

        es = QLabel(""); es.setObjectName("EmptySub")
        es.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(es)
        setattr(self, f"{prefix}empty_sub", es)

        layout.addWidget(empty_box, 1)
        empty_box.setVisible(False)

    # --------------------------------------------------------
    # النصوص
    # --------------------------------------------------------
    def _reload_texts(self):
        lang = self.language
        self.title.setText(_t("title", lang))
        self.subtitle.setText(_t("subtitle", lang))
        self.export_btn.setText(_t("btn_export", lang))

        self.tabs.setTabText(0, _t("tab_archived", lang))
        self.tabs.setTabText(1, _t("tab_drafts", lang))

        self.search_input.setPlaceholderText(_t("search_ph", lang))
        self.d_search_input.setPlaceholderText(_t("search_ph", lang))

        current_sup = self.sup_filter.currentData() if self.sup_filter.count() else None
        self.sup_filter.blockSignals(True)
        self.sup_filter.clear()
        self.sup_filter.addItem(_t("filter_sup", lang), None)
        for s in supplier_service.get_all(sort="name_asc"):
            self.sup_filter.addItem(s["name"], s["id"])
        for i in range(self.sup_filter.count()):
            if self.sup_filter.itemData(i) == current_sup:
                self.sup_filter.setCurrentIndex(i); break
        self.sup_filter.blockSignals(False)

        for sort_combo in (self.sort_combo, self.d_sort_combo):
            current = sort_combo.currentData() if sort_combo.count() else "newest"
            sort_combo.blockSignals(True)
            sort_combo.clear()
            for key in ["newest", "oldest", "profit_high", "profit_low", "usd_high"]:
                sort_combo.addItem(_t(f"sort_{key}", lang), key)
            for i in range(sort_combo.count()):
                if sort_combo.itemData(i) == current:
                    sort_combo.setCurrentIndex(i); break
            sort_combo.blockSignals(False)

        current_date = self.date_combo.currentData() if self.date_combo.count() else "all"
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItem(_t("filter_date", lang), "all")
        self.date_combo.addItem(_t("filter_custom", lang), "custom")
        for i in range(self.date_combo.count()):
            if self.date_combo.itemData(i) == current_date:
                self.date_combo.setCurrentIndex(i); break
        self.date_combo.blockSignals(False)

        self.from_lbl.setText(_t("date_from", lang))
        self.to_lbl.setText(_t("date_to", lang))
        self.reset_btn.setText(_t("btn_reset", lang))

        headers = [
            _t("col_num", lang), _t("col_inv_no", lang),
            _t("col_supplier", lang), _t("col_sup_inv", lang),
            _t("col_items", lang), _t("col_usd", lang),
            _t("col_cost", lang), _t("col_profit", lang),
            _t("col_actions", lang),
        ]
        for tbl in (self.table, self.d_table):
            tbl.setHorizontalHeaderLabels(headers)
            h = tbl.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
            h.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            tbl.setColumnWidth(0, 50)
            tbl.setColumnWidth(8, self.ACTIONS_COL_WIDTH)

        self.empty_title.setText(_t("no_archived", lang))
        self.empty_sub.setText(_t("empty_archived_sub", lang))
        self.d_empty_title.setText(_t("no_drafts", lang))
        self.d_empty_sub.setText(_t("empty_drafts_sub", lang))

    # --------------------------------------------------------
    # Events
    # --------------------------------------------------------
    def _on_tab_changed(self, index):
        self.current_status = "archived" if index == 0 else "draft"
        self.refresh()

    def _on_date_filter_changed(self):
        mode = self.date_combo.currentData() or "all"
        self.date_filter_mode = mode
        is_custom = (mode == "custom")
        self.from_lbl.setVisible(is_custom)
        self.from_date.setVisible(is_custom)
        self.to_lbl.setVisible(is_custom)
        self.to_date.setVisible(is_custom)
        self.refresh()

    def _reset_filters(self):
        self.search_input.clear()
        self.sup_filter.setCurrentIndex(0)
        self.sort_combo.setCurrentIndex(0)
        self.date_combo.setCurrentIndex(0)
        self.refresh()

    # --------------------------------------------------------
    # Refresh
    # --------------------------------------------------------
    def refresh(self):
        if self.current_status == "archived":
            self._refresh_archived()
        else:
            self._refresh_drafts()

    def _refresh_archived(self):
        search = self.search_input.text().strip()
        sup_id = self.sup_filter.currentData()
        sort = self.sort_combo.currentData() or "newest"

        date_from = ""
        date_to = ""
        if self.date_filter_mode == "custom":
            date_from = self.from_date.date().toString("yyyy-MM-dd")
            date_to = self.to_date.date().toString("yyyy-MM-dd")

        filters = dict(status="archived", search=search, supplier_id=sup_id,
                       date_from=date_from, date_to=date_to, sort=sort)
        self._list_filters = filters
        total = invoice_service.get_all(**filters, count_only=True)
        self.pager.configure(filters, total, self.language)
        rows = invoice_service.get_all(**filters, limit=self.pager.size, offset=self.pager.offset)
        self._fill_table(self.table, rows, is_draft=False)
        self.counter.setText(_t("count", self.language, n=total))

        if not rows:
            self.table.setVisible(False)
            self.empty_box.setVisible(True)
            if search or sup_id or date_from:
                self.empty_title.setText(_t("no_results", self.language))
                self.empty_sub.setText(_t("no_results_sub", self.language))
            else:
                self.empty_title.setText(_t("no_archived", self.language))
                self.empty_sub.setText(_t("empty_archived_sub", self.language))
        else:
            self.table.setVisible(True)
            self.empty_box.setVisible(False)

    def _refresh_drafts(self):
        search = self.d_search_input.text().strip()
        sort = self.d_sort_combo.currentData() or "newest"

        filters = dict(status="draft", search=search, sort=sort)
        self._list_filters = filters
        total = invoice_service.get_all(**filters, count_only=True)
        self.d_pager.configure(filters, total, self.language)
        rows = invoice_service.get_all(**filters, limit=self.d_pager.size, offset=self.d_pager.offset)
        self._fill_table(self.d_table, rows, is_draft=True)
        self.d_counter.setText(_t("count", self.language, n=total))

        if not rows:
            self.d_table.setVisible(False)
            self.d_empty_box.setVisible(True)
            if search:
                self.d_empty_title.setText(_t("no_results", self.language))
                self.d_empty_sub.setText(_t("no_results_sub", self.language))
            else:
                self.d_empty_title.setText(_t("no_drafts", self.language))
                self.d_empty_sub.setText(_t("empty_drafts_sub", self.language))
        else:
            self.d_table.setVisible(True)
            self.d_empty_box.setVisible(False)

    def _fill_table(self, table, rows, is_draft=False):
        self._visible_invoices = rows
        table.setRowCount(len(rows))
        for i, inv in enumerate(rows):
            it = QTableWidgetItem(str((self.d_pager if is_draft else self.pager).offset + i + 1))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 0, it)

            inv_item = QTableWidgetItem(inv["invoice_no"])
            inv_item.setData(Qt.ItemDataRole.UserRole, inv["id"])
            inv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 1, inv_item)

            table.setItem(i, 2, QTableWidgetItem(inv.get("supplier_name") or "—"))
            table.setItem(i, 3, QTableWidgetItem(inv.get("supplier_invoice_no") or "—"))

            total_qty = inv.get("total_qty", 0)
            it_qty = QTableWidgetItem(_fmt_num(total_qty))
            it_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 4, it_qty)

            usd_item = QTableWidgetItem(f"$ {_fmt_money(inv.get('total_usd'))}")
            usd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 5, usd_item)

            cost_item = QTableWidgetItem(f"{_fmt_money(inv.get('net_cost'))} د.ل")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 6, cost_item)

            profit = inv.get("total_profit", 0)
            profit_str = f"{_fmt_money(profit)} د.ل"
            if is_draft:
                profit_str = f"~ {profit_str}"
            profit_item = QTableWidgetItem(profit_str)
            profit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if profit < 0:
                profit_item.setForeground(Qt.GlobalColor.red)
            else:
                profit_item.setForeground(QColor(self.palette_data["text"]) if self.theme == "light" else Qt.GlobalColor.white)
            table.setItem(i, 7, profit_item)

            table.setCellWidget(i, 8, self._make_actions_widget(inv, is_draft))

    def _make_actions_widget(self, inv, is_draft):
        w = QWidget()
        w.setMinimumWidth(self.ACTIONS_COL_WIDTH - 20)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        view_btn = QPushButton("👁")
        view_btn.setObjectName("IconBtn")
        view_btn.setToolTip("View")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setFixedSize(34, 34)
        view_btn.clicked.connect(lambda: self._on_view(inv))
        layout.addWidget(view_btn)

        if is_draft:
            edit_btn = QPushButton("✏")
            edit_btn.setObjectName("IconBtn")
            edit_btn.setToolTip("Edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setFixedSize(34, 34)
            edit_btn.clicked.connect(lambda: self._on_edit(inv))
            layout.addWidget(edit_btn)

        pdf_btn = QPushButton("📄")
        pdf_btn.setObjectName("IconBtn")
        pdf_btn.setToolTip("PDF")
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setFixedSize(34, 34)
        pdf_btn.clicked.connect(lambda: self._on_pdf(inv))
        layout.addWidget(pdf_btn)

        excel_btn = QPushButton("📊")
        excel_btn.setObjectName("IconBtn")
        excel_btn.setToolTip("Excel")
        excel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        excel_btn.setFixedSize(34, 34)
        excel_btn.clicked.connect(lambda: self._on_excel(inv))
        layout.addWidget(excel_btn)

        if not is_draft:
            dup_btn = QPushButton("📋")
            dup_btn.setObjectName("IconBtn")
            dup_btn.setToolTip("Duplicate")
            dup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dup_btn.setFixedSize(34, 34)
            dup_btn.clicked.connect(lambda: self._on_duplicate(inv))
            layout.addWidget(dup_btn)

        del_btn = QPushButton("🗑")
        del_btn.setObjectName("IconBtnDanger")
        del_btn.setToolTip("Delete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(34, 34)
        del_btn.clicked.connect(lambda: self._on_delete(inv))
        layout.addWidget(del_btn)

        return w

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------
    def _on_view(self, inv):
        full = invoice_service.get_by_id(inv["id"])
        if not full:
            return
        dlg = InvoiceDetailsDialog(self, self.language, self.theme, full)
        dlg.exec()

    def _on_edit(self, inv):
        self.edit_draft_requested.emit(inv["id"])

    def _on_pdf(self, inv):
        full = invoice_service.get_by_id(inv["id"])
        if not full:
            QMessageBox.warning(self, _t("err_title", self.language),
                                _t("inv_not_found", self.language))
            return

        _preview_invoice_pdf(self, full, self.language, self.theme)

    def _on_excel(self, inv):
        full = invoice_service.get_by_id(inv["id"])
        if not full:
            QMessageBox.warning(self, _t("err_title", self.language),
                                _t("inv_not_found", self.language))
            return

        sections = self._load_default_sections()
        columns = self._load_default_columns()
        supplier_fields = self._load_default_supplier_fields()

        dlg = ExportContentDialog(
            self, self.language, self.theme,
            sections, columns, supplier_fields,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_sections = dlg.get_sections()
        selected_columns = dlg.get_columns()
        selected_supplier = dlg.get_supplier_fields()

        default_name = f"{safe_filename(full['invoice_no'])}_{date.today().isoformat()}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            _t("excel_save_title", self.language),
            default_name,
            "Excel (*.xlsx)",
        )
        if not file_path:
            return

        try:
            export_service.export_invoice_excel(
                full, file_path,
                sections=selected_sections,
                columns=selected_columns,
                supplier_fields=selected_supplier,
            )
            QMessageBox.information(
                self,
                _t("info_title", self.language),
                _t("excel_saved", self.language, path=file_path),
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                _t("err_title", self.language),
                _t("excel_err", self.language, err=str(e)),
            )

    def _load_default_sections(self):
        return _load_default_sections()

    def _load_default_columns(self):
        return _load_default_columns()

    def _load_default_supplier_fields(self):
        return _load_default_supplier_fields()

    def _on_export_list(self):
        rows = invoice_service.get_all(**getattr(self, "_list_filters", {"status": self.current_status}))
        if not rows:
            QMessageBox.information(self, _t("info_title", self.language), _t("no_results", self.language));return
        path, selected = QFileDialog.getSaveFileName(self, _t("btn_export", self.language), "Invoices.xlsx", "Excel (*.xlsx);;PDF (*.pdf)")
        if not path:return
        from app.services.export_service import ReportData
        keys = ("invoice_no", "supplier_name", "supplier_invoice_no", "invoice_date", "total_qty", "total_usd", "total_profit")
        labels = ["رقم الفاتورة", "المورد", "فاتورة المورد", "التاريخ", "Qty", "Total $", "الربح"] if self.language == "ar" else ["Invoice", "Supplier", "Supplier Invoice", "Date", "Qty", "Total $", "Profit"]
        report = ReportData("الفواتير" if self.language == "ar" else "Invoices", labels, [[row.get(key, "") for key in keys] for row in rows])
        try:
            if "PDF" in selected or path.lower().endswith(".pdf"):
                if not path.lower().endswith(".pdf"):path += ".pdf"
                export_service.export_pdf(report, path)
            else:
                if not path.lower().endswith(".xlsx"):path += ".xlsx"
                export_service.export_excel(report, path)
            saved_message = "pdf_saved" if path.lower().endswith(".pdf") else "excel_saved"
            QMessageBox.information(self, _t("info_title", self.language), _t(saved_message, self.language, path=path))
        except Exception as error:QMessageBox.warning(self, _t("err_title", self.language), str(error))

    def _on_duplicate(self, inv):
        """ينسخ الفاتورة المؤرشفة إلى مسودة جديدة ويفتحها للتعديل."""
        try:
            new_id = invoice_service.duplicate_invoice(inv["id"])
        except InvoiceError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))
            return

        # فتح المسودة الجديدة في صفحة New Invoice
        self.edit_draft_requested.emit(new_id)

    def _on_delete(self, inv):
        dlg = DeleteConfirmDialog(self, self.language, inv["invoice_no"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                invoice_service.delete(inv["id"])
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, _t("err_title", self.language),
                                    f"{_t('err_delete', self.language)}\n{e}")

    def _on_row_double_clicked(self, item):
        row = item.row()
        table = item.tableWidget()
        id_item = table.item(row, 1)
        if not id_item:
            return
        inv_id = id_item.data(Qt.ItemDataRole.UserRole)
        full = invoice_service.get_by_id(inv_id)
        if full:
            dlg = InvoiceDetailsDialog(self, self.language, self.theme, full)
            dlg.exec()

    def reload_language(self, language):
        self.language = language
        self._reload_texts()
        self.refresh()

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; color: #FFFFFF; }
            QFrame#HeaderCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(37, 99, 235, 0.18), stop:1 rgba(37, 99, 235, 0.02)); border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 14px; }
            QLabel#PageTitle { color: #FFFFFF; font-size: 22px; font-weight: 700; background: transparent; }
            QLabel#PageSub { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#CounterLabel { color: rgba(148,163,184,0.85); font-size: 13px; background: transparent; }
            QLabel#Muted { color: rgba(148,163,184,0.85); font-size: 13px; background: transparent; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(37, 99, 235, 0.15); border: 1px solid rgba(37, 99, 235, 0.5); }
            QLineEdit, QComboBox, QDateEdit { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 8px 14px; font-size: 14px; }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border: 1px solid #2563EB; }
            QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView { background-color: rgba(15, 29, 53, 0.98); color: #FFFFFF; selection-background-color: #2563EB; border: 1px solid rgba(37, 99, 235, 0.5); border-radius: 8px; }
            QTableWidget { background-color: rgba(15, 29, 53, 0.5); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 12px; gridline-color: transparent; outline: none; font-size: 13px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid rgba(37, 99, 235, 0.12); }
            QTableWidget::item:selected { background-color: rgba(37, 99, 235, 0.25); }
            QHeaderView::section { background-color: rgba(10, 22, 40, 0.9); color: rgba(148,163,184,0.9); border: none; border-bottom: 1px solid rgba(37, 99, 235, 0.3); padding: 10px 8px; font-weight: 600; font-size: 12px; }
            QFrame#EmptyBox { background-color: rgba(15, 29, 53, 0.4); border: 1px dashed rgba(37, 99, 235, 0.3); border-radius: 12px; }
            QLabel#EmptyTitle { color: #FFFFFF; font-size: 20px; font-weight: 600; background: transparent; }
            QLabel#EmptySub { color: rgba(148,163,184,0.85); font-size: 14px; background: transparent; }
            QTabWidget#ArchiveTabs::pane { background-color: #000000; border: none; }
            QTabWidget#ArchiveTabs QTabBar { background-color: rgba(10, 22, 40, 0.95); }
            QTabWidget#ArchiveTabs QTabBar::tab { background-color: transparent; color: rgba(148,163,184,0.85); padding: 12px 24px; margin-right: 4px; border: none; border-bottom: 3px solid transparent; font-size: 14px; font-weight: 500; }
            QTabWidget#ArchiveTabs QTabBar::tab:selected { color: #FFFFFF; border-bottom: 3px solid #2563EB; background-color: rgba(37, 99, 235, 0.1); }
            QTabWidget#ArchiveTabs QTabBar::tab:hover { color: #FFFFFF; background-color: rgba(255,255,255,0.04); }
            QPushButton#IconBtn { background-color: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 8px; font-size: 15px; padding: 0; }
            QPushButton#IconBtn:hover { background-color: rgba(37, 99, 235, 0.35); color: #FFFFFF; border: 1px solid rgba(59, 130, 246, 0.7); }
            QPushButton#IconBtnDanger { background-color: rgba(220, 38, 38, 0.15); color: #F87171; border: 1px solid rgba(220, 38, 38, 0.4); border-radius: 8px; font-size: 15px; padding: 0; }
            QPushButton#IconBtnDanger:hover { background-color: rgba(220, 38, 38, 0.35); color: #FFFFFF; border: 1px solid rgba(239, 68, 68, 0.7); }
            QScrollBar:vertical { background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
