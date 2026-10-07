"""
صفحة التقارير — 6 تقارير مع لوحة جانبية + تصدير PDF/Excel.
"""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QStackedWidget,
    QMessageBox, QFileDialog,
)

from app.config import CATEGORIES, CATEGORIES_AR
from app.services.reports_service import reports_service
from app.services.supplier_service import supplier_service
from app.services.product_service import product_service
from app.services.export_service import export_service, ReportData
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.charts import ProfitLineChart, PaymentsVsProfitChart
from app.ui.pdf_preview import show_pdf_preview
from app.ui.theme import set_widget_stylesheet


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "title":        ("Reports",                    "التقارير"),
    "subtitle":     ("Analyze your business performance.",
                     "تحليل أداء نشاطك التجاري."),

    "sec_entity":   ("By Entity",                  "حسب الكيان"),
    "sec_finance":  ("By Finance",                 "حسب المالية"),
    "sec_product":  ("By Product",                 "حسب الصنف"),

    "rep_supplier": ("Supplier Report",            "تقرير المورد"),
    "rep_profit":   ("Profit Report",              "تقرير الأرباح"),
    "rep_period":   ("Period Report",              "تقرير الفترة"),
    "rep_prices":   ("Price Changes",              "تغيّر الأسعار"),
    "rep_most_profitable": ("Most Profitable",     "الأكثر ربحية"),
    "rep_best_selling":    ("Best Selling",        "الأكثر مبيعًا"),

    "filter_supplier": ("Supplier",                "المورد"),
    "filter_product":  ("Product",                 "Product"),
    "filter_period":   ("Period",                  "الفترة"),
    "filter_category": ("Category",                "التصنيف"),
    "filter_top":      ("Top",                     "أعلى"),
    "filter_from":     ("From",                    "من"),
    "filter_to":       ("To",                      "إلى"),
    "all_suppliers":   ("All Suppliers",           "كل الموردين"),
    "all_categories":  ("All Categories",          "كل التصنيفات"),
    "select_product":  ("Select product...",       "اختر صنفًا..."),
    "select_supplier": ("Select supplier...",      "اختر موردًا..."),

    "period_month":    ("This Month",              "هذا الشهر"),
    "period_quarter":  ("This Quarter",            "هذا الربع"),
    "period_year":     ("This Year",               "هذه السنة"),
    "period_all":      ("All Time",                "كل الوقت"),

    "kpi_invoices":    ("Invoices",                "الفواتير"),
    "kpi_payments":    ("Payments",                "المدفوعات"),
    "kpi_usd":         ("Total USD",               "القيمة $"),
    "kpi_profit":      ("Profit",                  "الربح"),
    "kpi_sales":       ("Sales",                   "البيع"),
    "kpi_margin":      ("Avg Margin",              "متوسط الهامش"),
    "kpi_qty":         ("Total Qty",               "Total Qty"),
    "kpi_top":         ("Top Value",               "أعلى قيمة"),
    "kpi_products":    ("Products",                "الأصناف"),

    "col_inv_no":      ("Invoice No.",             "رقم الفاتورة"),
    "col_date":        ("Date",                    "التاريخ"),
    "col_supplier":    ("Supplier",                "المورد"),
    "col_usd":         ("Total USD",               "القيمة $"),
    "col_cost":        ("Net Cost",                "التكلفة"),
    "col_profit":      ("Profit",                  "الربح"),
    "col_qty":         ("Total Qty",               "Total Qty"),
    "col_code":        ("Code",                    "الكود"),
    "col_product":     ("Product",                 "Product"),
    "col_category":    ("Category",                "التصنيف"),
    "col_sales":       ("Sales",                   "البيع"),
    "col_margin":      ("Margin",                  "الهامش"),
    "col_purchase":    ("Price $",              "الشراء $"),
    "col_sale_dzd":    ("Sale LYD",                "البيع د.ل"),
    "col_change_p":    ("Δ Purchase",              "Δ الشراء"),
    "col_change_s":    ("Δ Sale",                  "Δ البيع"),
    "col_inv_count":   ("Invoices",                "الفواتير"),

    "chart_trend":     ("Monthly Trend",           "الاتجاه الشهري"),

    "btn_pdf":         ("📄 PDF",                  "📄 PDF"),
    "btn_excel":       ("📊 Excel",                "📊 Excel"),

    "no_data":         ("No data for the selected filters.",
                        "لا توجد بيانات للفلاتر المختارة."),

    "export_title_pdf": ("Save PDF",               "حفظ PDF"),
    "export_title_xls": ("Save Excel",             "حفظ Excel"),
    "export_success":   ("Exported successfully:\n{path}",
                         "تم التصدير بنجاح:\n{path}"),
    "export_err":       ("Export failed: {err}",   "فشل التصدير: {err}"),
    "export_no_data":   ("Nothing to export.",     "لا يوجد شيء للتصدير."),
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


def _cat_label(cat, language):
    if language == "ar":
        try:
            return CATEGORIES_AR[CATEGORIES.index(cat)]
        except ValueError:
            return cat
    return cat


# ============================================================
# KPI Card
# ============================================================
class SmallKpi(QFrame):
    def __init__(self, label: str, value: str = "—", color: str = "#2563EB"):
        super().__init__()
        self.setObjectName("KpiCard")
        self.setMinimumHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.lbl = QLabel(label)
        self.lbl.setObjectName("KpiTitle")
        layout.addWidget(self.lbl)

        self.val = QLabel(value)
        self.val.setObjectName("KpiValue")
        set_widget_stylesheet(self.val, f"color: {color};")
        layout.addWidget(self.val)

    def set_value(self, v: str):
        self.val.setText(v)

    def set_label(self, v: str):
        self.lbl.setText(v)


# ============================================================
# الصفحة الرئيسية
# ============================================================
class ReportsPage(QWidget):

    def __init__(self, theme="dark", language="en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.current_report = "supplier"
        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self._switch_report("supplier")

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("ReportsSidebar")
        self.sidebar.setFixedWidth(240)
        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(16, 20, 16, 20)
        sl.setSpacing(6)

        self.sidebar_buttons = {}
        self._section_labels = []

        sl.addWidget(self._make_section_label("sec_entity"))
        sl.addWidget(self._make_sidebar_button("supplier"))

        sl.addSpacing(14)
        sl.addWidget(self._make_section_label("sec_finance"))
        sl.addWidget(self._make_sidebar_button("profit"))
        sl.addWidget(self._make_sidebar_button("period"))

        sl.addSpacing(14)
        sl.addWidget(self._make_section_label("sec_product"))
        sl.addWidget(self._make_sidebar_button("prices"))
        sl.addWidget(self._make_sidebar_button("most_profitable"))
        sl.addWidget(self._make_sidebar_button("best_selling"))

        sl.addStretch()
        outer.addWidget(self.sidebar)

        # Content
        right_col = QWidget()
        right_col.setObjectName("ReportsContent")
        rl = QVBoxLayout(right_col)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(28, 18, 28, 18)

        text_col = QVBoxLayout(); text_col.setSpacing(2)
        self.title = QLabel(""); self.title.setObjectName("PageTitle")
        text_col.addWidget(self.title)
        self.subtitle = QLabel(""); self.subtitle.setObjectName("PageSub")
        text_col.addWidget(self.subtitle)
        hl.addLayout(text_col); hl.addStretch()

        rl.addWidget(header_card)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ReportsStack")

        self.report_supplier = self._build_supplier_report()
        self.report_profit = self._build_profit_report()
        self.report_period = self._build_period_report()
        self.report_prices = self._build_prices_report()
        self.report_most_profitable = self._build_most_profitable_report()
        self.report_best_selling = self._build_best_selling_report()

        self.stack.addWidget(self.report_supplier)
        self.stack.addWidget(self.report_profit)
        self.stack.addWidget(self.report_period)
        self.stack.addWidget(self.report_prices)
        self.stack.addWidget(self.report_most_profitable)
        self.stack.addWidget(self.report_best_selling)

        rl.addWidget(self.stack, 1)
        outer.addWidget(right_col, 1)

    def _make_section_label(self, text_key):
        lbl = QLabel(_t(text_key, self.language))
        lbl.setObjectName("ReportsSectionLabel")
        lbl.setProperty("text_key", text_key)
        self._section_labels.append(lbl)
        return lbl

    def _make_sidebar_button(self, key):
        btn = QPushButton("")
        btn.setObjectName("ReportsNavBtn")
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(42)
        btn.setCheckable(True)
        btn.setProperty("report_key", key)
        btn.clicked.connect(lambda _, k=key: self._switch_report(k))
        self.sidebar_buttons[key] = btn
        return btn

    def _make_export_buttons(self, report_key: str):
        """يُرجع (btn_pdf, btn_excel) مربوطة بالتقرير."""
        pdf_btn = QPushButton(_t("btn_pdf", self.language))
        pdf_btn.setObjectName("ExportBtn")
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setMinimumHeight(38)
        pdf_btn.setMinimumWidth(110)
        pdf_btn.clicked.connect(lambda: self._on_export(report_key, "pdf"))

        xls_btn = QPushButton(_t("btn_excel", self.language))
        xls_btn.setObjectName("ExportBtn")
        xls_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        xls_btn.setMinimumHeight(38)
        xls_btn.setMinimumWidth(110)
        xls_btn.clicked.connect(lambda: self._on_export(report_key, "excel"))

        return pdf_btn, xls_btn

    # --------------------------------------------------------
    # 1) تقرير المورد
    # --------------------------------------------------------
    def _build_supplier_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.sup_filter_lbl = QLabel(""); self.sup_filter_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.sup_filter_lbl)
        self.sup_filter = QComboBox()
        self.sup_filter.setMinimumHeight(40); self.sup_filter.setMinimumWidth(220)
        self.sup_filter.currentIndexChanged.connect(self._refresh_supplier)
        filters.addWidget(self.sup_filter)

        self.sup_period_lbl = QLabel(""); self.sup_period_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.sup_period_lbl)
        self.sup_period = QComboBox()
        self.sup_period.setMinimumHeight(40); self.sup_period.setMinimumWidth(150)
        self.sup_period.currentIndexChanged.connect(self._refresh_supplier)
        filters.addWidget(self.sup_period)

        filters.addStretch()

        self.sup_pdf_btn, self.sup_xls_btn = self._make_export_buttons("supplier")
        filters.addWidget(self.sup_pdf_btn)
        filters.addWidget(self.sup_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.sup_kpis = {
            "invoices_count": SmallKpi("Invoices", "0", "#2563EB"),
            "total_payments": SmallKpi("Payments", "0", "#0EA5E9"),
            "total_usd":      SmallKpi("USD", "0", "#22C55E"),
            "total_profit":   SmallKpi("Profit", "0", "#F59E0B"),
        }
        for k in self.sup_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        chart_card = QFrame(); chart_card.setObjectName("Card")
        ccl = QVBoxLayout(chart_card)
        ccl.setContentsMargins(16, 14, 16, 14); ccl.setSpacing(8)
        self.sup_chart_title = QLabel(""); self.sup_chart_title.setObjectName("CardTitle")
        ccl.addWidget(self.sup_chart_title)
        self.sup_chart = ProfitLineChart(self.theme)
        self.sup_chart.setMinimumHeight(240)
        ccl.addWidget(self.sup_chart)
        layout.addWidget(chart_card)

        self.sup_table = self._make_table()
        layout.addWidget(self.sup_table, 1)
        return w

    # --------------------------------------------------------
    # 2) تقرير الأرباح
    # --------------------------------------------------------
    def _build_profit_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.profit_period_lbl = QLabel(""); self.profit_period_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.profit_period_lbl)
        self.profit_period = QComboBox()
        self.profit_period.setMinimumHeight(40); self.profit_period.setMinimumWidth(150)
        self.profit_period.currentIndexChanged.connect(self._refresh_profit)
        filters.addWidget(self.profit_period)
        filters.addStretch()

        self.profit_pdf_btn, self.profit_xls_btn = self._make_export_buttons("profit")
        filters.addWidget(self.profit_pdf_btn)
        filters.addWidget(self.profit_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.profit_kpis = {
            "invoices_count": SmallKpi("Invoices", "0", "#2563EB"),
            "total_sales":    SmallKpi("Sales", "0", "#0EA5E9"),
            "total_profit":   SmallKpi("Profit", "0", "#22C55E"),
            "avg_margin":     SmallKpi("Margin", "0%", "#F59E0B"),
        }
        for k in self.profit_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        chart_card = QFrame(); chart_card.setObjectName("Card")
        ccl = QVBoxLayout(chart_card)
        ccl.setContentsMargins(16, 14, 16, 14); ccl.setSpacing(8)
        self.profit_chart_title = QLabel(""); self.profit_chart_title.setObjectName("CardTitle")
        ccl.addWidget(self.profit_chart_title)
        self.profit_chart = ProfitLineChart(self.theme)
        self.profit_chart.setMinimumHeight(240)
        ccl.addWidget(self.profit_chart)
        layout.addWidget(chart_card)

        self.profit_table = self._make_table()
        layout.addWidget(self.profit_table, 1)
        return w

    # --------------------------------------------------------
    # 3) تقرير الفترة
    # --------------------------------------------------------
    def _build_period_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.period_from_lbl = QLabel(""); self.period_from_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.period_from_lbl)
        self.period_from = QDateEdit()
        self.period_from.setCalendarPopup(True)
        self.period_from.setDate(QDate.currentDate().addMonths(-1))
        self.period_from.setDisplayFormat("yyyy-MM-dd")
        self.period_from.setMinimumHeight(40)
        self.period_from.dateChanged.connect(self._refresh_period)
        filters.addWidget(self.period_from)

        self.period_to_lbl = QLabel(""); self.period_to_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.period_to_lbl)
        self.period_to = QDateEdit()
        self.period_to.setCalendarPopup(True)
        self.period_to.setDate(QDate.currentDate())
        self.period_to.setDisplayFormat("yyyy-MM-dd")
        self.period_to.setMinimumHeight(40)
        self.period_to.dateChanged.connect(self._refresh_period)
        filters.addWidget(self.period_to)

        self.period_sup_lbl = QLabel(""); self.period_sup_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.period_sup_lbl)
        self.period_sup = QComboBox()
        self.period_sup.setMinimumHeight(40); self.period_sup.setMinimumWidth(200)
        self.period_sup.currentIndexChanged.connect(self._refresh_period)
        filters.addWidget(self.period_sup)
        filters.addStretch()

        self.period_pdf_btn, self.period_xls_btn = self._make_export_buttons("period")
        filters.addWidget(self.period_pdf_btn)
        filters.addWidget(self.period_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.period_kpis = {
            "invoices_count": SmallKpi("Invoices", "0", "#2563EB"),
            "total_payments": SmallKpi("Payments", "0", "#0EA5E9"),
            "total_usd":      SmallKpi("USD", "0", "#22C55E"),
            "total_profit":   SmallKpi("Profit", "0", "#F59E0B"),
        }
        for k in self.period_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        chart_card = QFrame(); chart_card.setObjectName("Card")
        ccl = QVBoxLayout(chart_card)
        ccl.setContentsMargins(16, 14, 16, 14); ccl.setSpacing(8)
        self.period_chart_title = QLabel(""); self.period_chart_title.setObjectName("CardTitle")
        ccl.addWidget(self.period_chart_title)
        self.period_chart = ProfitLineChart(self.theme)
        self.period_chart.setMinimumHeight(240)
        ccl.addWidget(self.period_chart)
        layout.addWidget(chart_card)

        self.period_table = self._make_table()
        layout.addWidget(self.period_table, 1)
        return w

    # --------------------------------------------------------
    # 4) تقرير تغيّر الأسعار
    # --------------------------------------------------------
    def _build_prices_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.price_prod_lbl = QLabel(""); self.price_prod_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.price_prod_lbl)
        self.price_prod = QComboBox()
        self.price_prod.setMinimumHeight(40); self.price_prod.setMinimumWidth(280)
        self.price_prod.currentIndexChanged.connect(self._refresh_prices)
        filters.addWidget(self.price_prod)

        self.price_period_lbl = QLabel(""); self.price_period_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.price_period_lbl)
        self.price_period = QComboBox()
        self.price_period.setMinimumHeight(40); self.price_period.setMinimumWidth(150)
        self.price_period.currentIndexChanged.connect(self._refresh_prices)
        filters.addWidget(self.price_period)
        filters.addStretch()

        self.price_pdf_btn, self.price_xls_btn = self._make_export_buttons("prices")
        filters.addWidget(self.price_pdf_btn)
        filters.addWidget(self.price_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.price_kpis = {
            "first_purchase": SmallKpi("First $", "0", "#2563EB"),
            "last_purchase":  SmallKpi("Last $", "0", "#0EA5E9"),
            "first_sale":     SmallKpi("First د.ل", "0", "#22C55E"),
            "last_sale":      SmallKpi("Last د.ل", "0", "#F59E0B"),
        }
        for k in self.price_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        chart_card = QFrame(); chart_card.setObjectName("Card")
        ccl = QVBoxLayout(chart_card)
        ccl.setContentsMargins(16, 14, 16, 14); ccl.setSpacing(8)
        self.price_chart_title = QLabel(""); self.price_chart_title.setObjectName("CardTitle")
        ccl.addWidget(self.price_chart_title)
        self.price_chart = ProfitLineChart(self.theme)
        self.price_chart.setMinimumHeight(240)
        ccl.addWidget(self.price_chart)
        layout.addWidget(chart_card)

        self.price_table = self._make_table()
        layout.addWidget(self.price_table, 1)
        return w

    # --------------------------------------------------------
    # 5) الأكثر ربحية
    # --------------------------------------------------------
    def _build_most_profitable_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.mp_period_lbl = QLabel(""); self.mp_period_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.mp_period_lbl)
        self.mp_period = QComboBox()
        self.mp_period.setMinimumHeight(40); self.mp_period.setMinimumWidth(150)
        self.mp_period.currentIndexChanged.connect(self._refresh_most_profitable)
        filters.addWidget(self.mp_period)

        self.mp_cat_lbl = QLabel(""); self.mp_cat_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.mp_cat_lbl)
        self.mp_cat = QComboBox()
        self.mp_cat.setMinimumHeight(40); self.mp_cat.setMinimumWidth(180)
        self.mp_cat.currentIndexChanged.connect(self._refresh_most_profitable)
        filters.addWidget(self.mp_cat)

        self.mp_top_lbl = QLabel(""); self.mp_top_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.mp_top_lbl)
        self.mp_top = QComboBox()
        self.mp_top.setMinimumHeight(40); self.mp_top.setMinimumWidth(100)
        self.mp_top.currentIndexChanged.connect(self._refresh_most_profitable)
        filters.addWidget(self.mp_top)
        filters.addStretch()

        self.mp_pdf_btn, self.mp_xls_btn = self._make_export_buttons("most_profitable")
        filters.addWidget(self.mp_pdf_btn)
        filters.addWidget(self.mp_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.mp_kpis = {
            "total_profit": SmallKpi("Total Profit", "0", "#22C55E"),
            "products_count": SmallKpi("Products", "0", "#2563EB"),
            "avg_margin": SmallKpi("Avg Margin", "0%", "#F59E0B"),
            "top_profit": SmallKpi("Top Value", "0", "#0EA5E9"),
        }
        for k in self.mp_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        self.mp_table = self._make_table()
        layout.addWidget(self.mp_table, 1)
        return w

    # --------------------------------------------------------
    # 6) الأكثر مبيعًا
    # --------------------------------------------------------
    def _build_best_selling_report(self):
        w = QWidget(); w.setObjectName("ReportPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        filters = QHBoxLayout(); filters.setSpacing(10)
        self.bs_period_lbl = QLabel(""); self.bs_period_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.bs_period_lbl)
        self.bs_period = QComboBox()
        self.bs_period.setMinimumHeight(40); self.bs_period.setMinimumWidth(150)
        self.bs_period.currentIndexChanged.connect(self._refresh_best_selling)
        filters.addWidget(self.bs_period)

        self.bs_cat_lbl = QLabel(""); self.bs_cat_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.bs_cat_lbl)
        self.bs_cat = QComboBox()
        self.bs_cat.setMinimumHeight(40); self.bs_cat.setMinimumWidth(180)
        self.bs_cat.currentIndexChanged.connect(self._refresh_best_selling)
        filters.addWidget(self.bs_cat)

        self.bs_top_lbl = QLabel(""); self.bs_top_lbl.setObjectName("FieldLabel")
        filters.addWidget(self.bs_top_lbl)
        self.bs_top = QComboBox()
        self.bs_top.setMinimumHeight(40); self.bs_top.setMinimumWidth(100)
        self.bs_top.currentIndexChanged.connect(self._refresh_best_selling)
        filters.addWidget(self.bs_top)
        filters.addStretch()

        self.bs_pdf_btn, self.bs_xls_btn = self._make_export_buttons("best_selling")
        filters.addWidget(self.bs_pdf_btn)
        filters.addWidget(self.bs_xls_btn)
        layout.addLayout(filters)

        kpis_row = QHBoxLayout(); kpis_row.setSpacing(12)
        self.bs_kpis = {
            "total_qty": SmallKpi("Total Qty", "0", "#22C55E"),
            "total_sales": SmallKpi("Sales", "0", "#0EA5E9"),
            "top_qty": SmallKpi("Top Qty", "0", "#2563EB"),
            "products_count": SmallKpi("Products", "0", "#F59E0B"),
        }
        for k in self.bs_kpis.values():
            kpis_row.addWidget(k, 1)
        layout.addLayout(kpis_row)

        self.bs_table = self._make_table()
        layout.addWidget(self.bs_table, 1)
        return w

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------
    def _make_table(self):
        tbl = QTableWidget()
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tbl.verticalHeader().setDefaultSectionSize(44)
        tbl.setMinimumHeight(220)
        return tbl

    def _set_headers(self, table, headers):
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels([_t(h, self.language) for h in headers])
        table.setRowCount(0)
        h = table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

    def _clear_table(self, table):
        table.setRowCount(0)

    # --------------------------------------------------------
    # النصوص + القوائم
    # --------------------------------------------------------
    def _reload_texts(self):
        lang = self.language
        self.title.setText(_t("title", lang))
        self.subtitle.setText(_t("subtitle", lang))

        for lbl in self._section_labels:
            lbl.setText(_t(lbl.property("text_key"), lang))

        for key, btn in self.sidebar_buttons.items():
            btn.setText(_t(f"rep_{key}", lang))

        # Export buttons
        for btn in (self.sup_pdf_btn, self.profit_pdf_btn, self.period_pdf_btn,
                    self.price_pdf_btn, self.mp_pdf_btn, self.bs_pdf_btn):
            btn.setText(_t("btn_pdf", lang))
        for btn in (self.sup_xls_btn, self.profit_xls_btn, self.period_xls_btn,
                    self.price_xls_btn, self.mp_xls_btn, self.bs_xls_btn):
            btn.setText(_t("btn_excel", lang))

        self.sup_filter_lbl.setText(_t("filter_supplier", lang))
        self.sup_period_lbl.setText(_t("filter_period", lang))
        self.profit_period_lbl.setText(_t("filter_period", lang))
        self.period_from_lbl.setText(_t("filter_from", lang))
        self.period_to_lbl.setText(_t("filter_to", lang))
        self.period_sup_lbl.setText(_t("filter_supplier", lang))
        self.price_prod_lbl.setText(_t("filter_product", lang))
        self.price_period_lbl.setText(_t("filter_period", lang))
        self.mp_period_lbl.setText(_t("filter_period", lang))
        self.mp_cat_lbl.setText(_t("filter_category", lang))
        self.mp_top_lbl.setText(_t("filter_top", lang))
        self.bs_period_lbl.setText(_t("filter_period", lang))
        self.bs_cat_lbl.setText(_t("filter_category", lang))
        self.bs_top_lbl.setText(_t("filter_top", lang))

        self.sup_chart_title.setText(_t("chart_trend", lang))
        self.profit_chart_title.setText(_t("chart_trend", lang))
        self.period_chart_title.setText(_t("chart_trend", lang))
        self.price_chart_title.setText(_t("chart_trend", lang))

        self.sup_kpis["invoices_count"].set_label(_t("kpi_invoices", lang))
        self.sup_kpis["total_payments"].set_label(_t("kpi_payments", lang))
        self.sup_kpis["total_usd"].set_label(_t("kpi_usd", lang))
        self.sup_kpis["total_profit"].set_label(_t("kpi_profit", lang))

        self.profit_kpis["invoices_count"].set_label(_t("kpi_invoices", lang))
        self.profit_kpis["total_sales"].set_label(_t("kpi_sales", lang))
        self.profit_kpis["total_profit"].set_label(_t("kpi_profit", lang))
        self.profit_kpis["avg_margin"].set_label(_t("kpi_margin", lang))

        self.period_kpis["invoices_count"].set_label(_t("kpi_invoices", lang))
        self.period_kpis["total_payments"].set_label(_t("kpi_payments", lang))
        self.period_kpis["total_usd"].set_label(_t("kpi_usd", lang))
        self.period_kpis["total_profit"].set_label(_t("kpi_profit", lang))

        self.price_kpis["first_purchase"].set_label("First $")
        self.price_kpis["last_purchase"].set_label("Last $")
        self.price_kpis["first_sale"].set_label("First د.ل")
        self.price_kpis["last_sale"].set_label("Last د.ل")

        self.mp_kpis["total_profit"].set_label(_t("kpi_profit", lang))
        self.mp_kpis["products_count"].set_label(_t("kpi_products", lang))
        self.mp_kpis["avg_margin"].set_label(_t("kpi_margin", lang))
        self.mp_kpis["top_profit"].set_label(_t("kpi_top", lang))

        self.bs_kpis["total_qty"].set_label(_t("kpi_qty", lang))
        self.bs_kpis["total_sales"].set_label(_t("kpi_sales", lang))
        self.bs_kpis["top_qty"].set_label(_t("kpi_top", lang))
        self.bs_kpis["products_count"].set_label(_t("kpi_products", lang))

        self._populate_period_combos()
        self._populate_supplier_combos()
        self._populate_product_combo()
        self._populate_category_combos()
        self._populate_top_combos()

    def _populate_period_combos(self):
        for combo in (self.sup_period, self.profit_period,
                      self.price_period, self.mp_period, self.bs_period):
            current = combo.currentData() if combo.count() else "year"
            combo.blockSignals(True)
            combo.clear()
            for key in ["month", "quarter", "year", "all"]:
                combo.addItem(_t(f"period_{key}", self.language), key)
            for i in range(combo.count()):
                if combo.itemData(i) == current:
                    combo.setCurrentIndex(i); break
            combo.blockSignals(False)

    def _populate_supplier_combos(self):
        for combo in (self.sup_filter, self.period_sup):
            current = combo.currentData() if combo.count() else None
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(_t("all_suppliers", self.language), None)
            for s in supplier_service.get_all(sort="name_asc"):
                combo.addItem(s["name"], s["id"])
            for i in range(combo.count()):
                if combo.itemData(i) == current:
                    combo.setCurrentIndex(i); break
            combo.blockSignals(False)

    def _populate_product_combo(self):
        current = self.price_prod.currentData() if self.price_prod.count() else None
        self.price_prod.blockSignals(True)
        self.price_prod.clear()
        self.price_prod.addItem(_t("select_product", self.language), None)
        for p in product_service.get_all(sort="name_asc"):
            self.price_prod.addItem(p["name"] + (" — " + p["pattern"] if p.get("pattern") else ""), p["id"])
        for i in range(self.price_prod.count()):
            if self.price_prod.itemData(i) == current:
                self.price_prod.setCurrentIndex(i); break
        self.price_prod.blockSignals(False)

    def _populate_category_combos(self):
        for combo in (self.mp_cat, self.bs_cat):
            current = combo.currentData() if combo.count() else ""
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(_t("all_categories", self.language), "")
            for cat in CATEGORIES:
                combo.addItem(_cat_label(cat, self.language), cat)
            for i in range(combo.count()):
                if combo.itemData(i) == current:
                    combo.setCurrentIndex(i); break
            combo.blockSignals(False)

    def _populate_top_combos(self):
        for combo in (self.mp_top, self.bs_top):
            current = combo.currentData() if combo.count() else 10
            combo.blockSignals(True)
            combo.clear()
            for n in [5, 10, 20, 50, 100]:
                combo.addItem(str(n), n)
            for i in range(combo.count()):
                if combo.itemData(i) == current:
                    combo.setCurrentIndex(i); break
            combo.blockSignals(False)

    # --------------------------------------------------------
    # Switch
    # --------------------------------------------------------
    def _switch_report(self, key):
        self.current_report = key
        indices = {
            "supplier": 0, "profit": 1, "period": 2,
            "prices": 3, "most_profitable": 4, "best_selling": 5,
        }
        self.stack.setCurrentIndex(indices.get(key, 0))

        for k, btn in self.sidebar_buttons.items():
            active = (k == key)
            btn.setProperty("active", active)
            btn.setChecked(active)
            btn.style().unpolish(btn); btn.style().polish(btn)

        if key == "supplier": self._refresh_supplier()
        elif key == "profit": self._refresh_profit()
        elif key == "period": self._refresh_period()
        elif key == "prices": self._refresh_prices()
        elif key == "most_profitable": self._refresh_most_profitable()
        elif key == "best_selling": self._refresh_best_selling()

    # --------------------------------------------------------
    # Refresh
    # --------------------------------------------------------
    def _refresh_supplier(self):
        sup_id = self.sup_filter.currentData()
        if not sup_id:
            self._clear_table(self.sup_table)
            for kpi in self.sup_kpis.values():
                kpi.set_value("—")
            self.sup_chart.set_data([])
            return
        period = self.sup_period.currentData() or "year"
        data = reports_service.supplier_report(sup_id, period)
        s = data["stats"]
        self.sup_kpis["invoices_count"].set_value(str(s["invoices_count"]))
        self.sup_kpis["total_payments"].set_value(f"{_fmt_money(s['total_payments'])} د.ل")
        self.sup_kpis["total_usd"].set_value(f"$ {_fmt_money(s['total_usd'])}")
        self.sup_kpis["total_profit"].set_value(f"{_fmt_money(s['total_profit'])} د.ل")
        self.sup_chart.set_data(data["trend"])
        self._fill_supplier_table(data["invoices"])

    def _fill_supplier_table(self, rows):
        headers = ["col_inv_no", "col_date", "col_qty", "col_usd", "col_cost", "col_profit"]
        self._set_headers(self.sup_table, headers)
        self.sup_table.setRowCount(len(rows))
        for i, inv in enumerate(rows):
            self.sup_table.setItem(i, 0, QTableWidgetItem(str(inv.get("invoice_no", ""))))
            self.sup_table.setItem(i, 1, QTableWidgetItem(str(inv.get("invoice_date", ""))))
            self.sup_table.setItem(i, 2, QTableWidgetItem(_fmt_num(inv.get("total_qty", 0))))
            self.sup_table.setItem(i, 3, QTableWidgetItem(f"$ {_fmt_money(inv.get('total_usd'))}"))
            self.sup_table.setItem(i, 4, QTableWidgetItem(f"{_fmt_money(inv.get('net_cost'))} د.ل"))
            self.sup_table.setItem(i, 5, QTableWidgetItem(f"{_fmt_money(inv.get('total_profit'))} د.ل"))

    def _refresh_profit(self):
        period = self.profit_period.currentData() or "year"
        data = reports_service.profit_report(period)
        s = data["stats"]
        self.profit_kpis["invoices_count"].set_value(str(s["invoices_count"]))
        self.profit_kpis["total_sales"].set_value(f"{_fmt_money(s['total_sales'])} د.ل")
        self.profit_kpis["total_profit"].set_value(f"{_fmt_money(s['total_profit'])} د.ل")
        self.profit_kpis["avg_margin"].set_value(f"{s['avg_margin']:.2f} %")
        self.profit_chart.set_data(data["monthly"])
        self._fill_profit_table(data["invoices"])

    def _fill_profit_table(self, rows):
        headers = ["col_inv_no", "col_date", "col_supplier", "col_profit", "col_margin"]
        self._set_headers(self.profit_table, headers)
        self.profit_table.setRowCount(len(rows))
        for i, inv in enumerate(rows):
            self.profit_table.setItem(i, 0, QTableWidgetItem(str(inv.get("invoice_no", ""))))
            self.profit_table.setItem(i, 1, QTableWidgetItem(str(inv.get("invoice_date", ""))))
            self.profit_table.setItem(i, 2, QTableWidgetItem(str(inv.get("supplier_name") or "—")))
            self.profit_table.setItem(i, 3, QTableWidgetItem(f"{_fmt_money(inv.get('total_profit'))} د.ل"))
            self.profit_table.setItem(i, 4, QTableWidgetItem(f"{inv.get('profit_margin', 0):.2f} %"))

    def _refresh_period(self):
        date_from = self.period_from.date().toString("yyyy-MM-dd")
        date_to = self.period_to.date().toString("yyyy-MM-dd")
        sup_id = self.period_sup.currentData()
        data = reports_service.period_report(date_from, date_to, sup_id)
        s = data["stats"]
        self.period_kpis["invoices_count"].set_value(str(s["invoices_count"]))
        self.period_kpis["total_payments"].set_value(f"{_fmt_money(s['total_payments'])} د.ل")
        self.period_kpis["total_usd"].set_value(f"$ {_fmt_money(s['total_usd'])}")
        self.period_kpis["total_profit"].set_value(f"{_fmt_money(s['total_profit'])} د.ل")
        trend = [{"month": r["date"][-5:], "value": r["value"]} for r in data["daily"]]
        self.period_chart.set_data(trend)
        self._fill_period_table(data["invoices"])

    def _fill_period_table(self, rows):
        headers = ["col_inv_no", "col_date", "col_supplier", "col_usd", "col_profit"]
        self._set_headers(self.period_table, headers)
        self.period_table.setRowCount(len(rows))
        for i, inv in enumerate(rows):
            self.period_table.setItem(i, 0, QTableWidgetItem(str(inv.get("invoice_no", ""))))
            self.period_table.setItem(i, 1, QTableWidgetItem(str(inv.get("invoice_date", ""))))
            self.period_table.setItem(i, 2, QTableWidgetItem(str(inv.get("supplier_name") or "—")))
            self.period_table.setItem(i, 3, QTableWidgetItem(f"$ {_fmt_money(inv.get('total_usd'))}"))
            self.period_table.setItem(i, 4, QTableWidgetItem(f"{_fmt_money(inv.get('total_profit'))} د.ل"))

    def _refresh_prices(self):
        pid = self.price_prod.currentData()
        if not pid:
            self._clear_table(self.price_table)
            for kpi in self.price_kpis.values():
                kpi.set_value("—")
            self.price_chart.set_data([])
            return
        period = self.price_period.currentData() or "year"
        data = reports_service.price_changes_report(pid, period)
        s = data["stats"]
        self.price_kpis["first_purchase"].set_value(f"$ {_fmt_money(s['first_purchase'])}")
        self.price_kpis["last_purchase"].set_value(f"$ {_fmt_money(s['last_purchase'])}")
        self.price_kpis["first_sale"].set_value(f"{_fmt_money(s['first_sale'])} د.ل")
        self.price_kpis["last_sale"].set_value(f"{_fmt_money(s['last_sale'])} د.ل")
        trend = [{"month": c["date"][-5:], "value": c["purchase_usd"]} for c in data["changes"]]
        self.price_chart.set_data(trend)
        self._fill_prices_table(data["changes"])

    def _fill_prices_table(self, rows):
        headers = ["col_date", "col_inv_no", "col_supplier",
                   "col_purchase", "col_sale_dzd", "col_change_p", "col_change_s"]
        self._set_headers(self.price_table, headers)
        self.price_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.price_table.setItem(i, 0, QTableWidgetItem(str(r.get("date", ""))))
            self.price_table.setItem(i, 1, QTableWidgetItem(str(r.get("invoice_no", ""))))
            self.price_table.setItem(i, 2, QTableWidgetItem(str(r.get("supplier_name") or "—")))
            self.price_table.setItem(i, 3, QTableWidgetItem(f"$ {_fmt_money(r.get('purchase_usd'))}"))
            self.price_table.setItem(i, 4, QTableWidgetItem(f"{_fmt_money(r.get('sale_dzd'))} د.ل"))
            cp = r.get("change_purchase")
            self.price_table.setItem(i, 5, QTableWidgetItem(
                f"{cp:+.2f} %" if cp is not None else "—"))
            cs = r.get("change_sale")
            self.price_table.setItem(i, 6, QTableWidgetItem(
                f"{cs:+.2f} %" if cs is not None else "—"))

    def _refresh_most_profitable(self):
        period = self.mp_period.currentData() or "year"
        category = self.mp_cat.currentData() or ""
        top_n = self.mp_top.currentData() or 10
        data = reports_service.most_profitable_report(period, category, top_n)
        s = data["stats"]
        self.mp_kpis["total_profit"].set_value(f"{_fmt_money(s['total_profit'])} د.ل")
        self.mp_kpis["products_count"].set_value(str(s["products_count"]))
        self.mp_kpis["avg_margin"].set_value(f"{s['avg_margin']:.2f} %")
        self.mp_kpis["top_profit"].set_value(f"{_fmt_money(s['top_profit'])} د.ل")
        self._fill_most_profitable_table(data["products"])

    def _fill_most_profitable_table(self, rows):
        headers = ["col_product", "col_category",
                   "col_qty", "col_sales", "col_profit", "col_margin"]
        self._set_headers(self.mp_table, headers)
        self.mp_table.setRowCount(len(rows))
        for i, p in enumerate(rows):
            self.mp_table.setItem(i, 0, QTableWidgetItem(str(p.get("name", "")) + (" — " + p["pattern"] if p.get("pattern") else "")))
            self.mp_table.setItem(i, 1, QTableWidgetItem(_cat_label(p.get("category", ""), self.language)))
            self.mp_table.setItem(i, 2, QTableWidgetItem(_fmt_num(p.get("total_qty", 0))))
            self.mp_table.setItem(i, 3, QTableWidgetItem(f"{_fmt_money(p.get('total_sales'))} د.ل"))
            self.mp_table.setItem(i, 4, QTableWidgetItem(f"{_fmt_money(p.get('total_profit'))} د.ل"))
            self.mp_table.setItem(i, 5, QTableWidgetItem(f"{p.get('margin', 0):.2f} %"))

    def _refresh_best_selling(self):
        period = self.bs_period.currentData() or "year"
        category = self.bs_cat.currentData() or ""
        top_n = self.bs_top.currentData() or 10
        data = reports_service.best_selling_report(period, category, top_n)
        s = data["stats"]
        self.bs_kpis["total_qty"].set_value(_fmt_num(s["total_qty"]))
        self.bs_kpis["total_sales"].set_value(f"{_fmt_money(s['total_sales'])} د.ل")
        self.bs_kpis["top_qty"].set_value(_fmt_num(s["top_qty"]))
        self.bs_kpis["products_count"].set_value(str(s["products_count"]))
        self._fill_best_selling_table(data["products"])

    def _fill_best_selling_table(self, rows):
        headers = ["col_product", "col_category",
                   "col_qty", "col_sales", "col_inv_count"]
        self._set_headers(self.bs_table, headers)
        self.bs_table.setRowCount(len(rows))
        for i, p in enumerate(rows):
            self.bs_table.setItem(i, 0, QTableWidgetItem(str(p.get("name", "")) + (" — " + p["pattern"] if p.get("pattern") else "")))
            self.bs_table.setItem(i, 1, QTableWidgetItem(_cat_label(p.get("category", ""), self.language)))
            self.bs_table.setItem(i, 2, QTableWidgetItem(_fmt_num(p.get("total_qty", 0))))
            self.bs_table.setItem(i, 3, QTableWidgetItem(f"{_fmt_money(p.get('total_sales'))} د.ل"))
            self.bs_table.setItem(i, 4, QTableWidgetItem(str(p.get("invoices_count", 0))))

    # ============================================================
    # التصدير
    # ============================================================
    def _get_report_data(self, report_key: str) -> ReportData | None:
        """يُعيد ReportData جاهز للتصدير."""
        lang = self.language

        if report_key == "supplier":
            if not self.sup_filter.currentData():
                return None
            return ReportData(
                title=_t("rep_supplier", lang),
                headers=[_t(h, lang) for h in
                         ["col_inv_no", "col_date", "col_qty", "col_usd", "col_cost", "col_profit"]],
                rows=self._table_to_rows(self.sup_table),
                kpis=[
                    (self.sup_kpis["invoices_count"].lbl.text(),
                     self.sup_kpis["invoices_count"].val.text()),
                    (self.sup_kpis["total_payments"].lbl.text(),
                     self.sup_kpis["total_payments"].val.text()),
                    (self.sup_kpis["total_usd"].lbl.text(),
                     self.sup_kpis["total_usd"].val.text()),
                    (self.sup_kpis["total_profit"].lbl.text(),
                     self.sup_kpis["total_profit"].val.text()),
                ],
            )

        if report_key == "profit":
            return ReportData(
                title=_t("rep_profit", lang),
                headers=[_t(h, lang) for h in
                         ["col_inv_no", "col_date", "col_supplier", "col_profit", "col_margin"]],
                rows=self._table_to_rows(self.profit_table),
                kpis=[
                    (self.profit_kpis["invoices_count"].lbl.text(),
                     self.profit_kpis["invoices_count"].val.text()),
                    (self.profit_kpis["total_sales"].lbl.text(),
                     self.profit_kpis["total_sales"].val.text()),
                    (self.profit_kpis["total_profit"].lbl.text(),
                     self.profit_kpis["total_profit"].val.text()),
                    (self.profit_kpis["avg_margin"].lbl.text(),
                     self.profit_kpis["avg_margin"].val.text()),
                ],
            )

        if report_key == "period":
            return ReportData(
                title=_t("rep_period", lang),
                headers=[_t(h, lang) for h in
                         ["col_inv_no", "col_date", "col_supplier", "col_usd", "col_profit"]],
                rows=self._table_to_rows(self.period_table),
                kpis=[
                    (self.period_kpis["invoices_count"].lbl.text(),
                     self.period_kpis["invoices_count"].val.text()),
                    (self.period_kpis["total_payments"].lbl.text(),
                     self.period_kpis["total_payments"].val.text()),
                    (self.period_kpis["total_usd"].lbl.text(),
                     self.period_kpis["total_usd"].val.text()),
                    (self.period_kpis["total_profit"].lbl.text(),
                     self.period_kpis["total_profit"].val.text()),
                ],
            )

        if report_key == "prices":
            if not self.price_prod.currentData():
                return None
            return ReportData(
                title=_t("rep_prices", lang),
                headers=[_t(h, lang) for h in
                         ["col_date", "col_inv_no", "col_supplier",
                          "col_purchase", "col_sale_dzd", "col_change_p", "col_change_s"]],
                rows=self._table_to_rows(self.price_table),
                kpis=[
                    ("First $", self.price_kpis["first_purchase"].val.text()),
                    ("Last $",  self.price_kpis["last_purchase"].val.text()),
                    ("First د.ل", self.price_kpis["first_sale"].val.text()),
                    ("Last د.ل",  self.price_kpis["last_sale"].val.text()),
                ],
            )

        if report_key == "most_profitable":
            return ReportData(
                title=_t("rep_most_profitable", lang),
                headers=[_t(h, lang) for h in
                         ["col_product", "col_category",
                          "col_qty", "col_sales", "col_profit", "col_margin"]],
                rows=self._table_to_rows(self.mp_table),
                kpis=[
                    (self.mp_kpis["total_profit"].lbl.text(),
                     self.mp_kpis["total_profit"].val.text()),
                    (self.mp_kpis["products_count"].lbl.text(),
                     self.mp_kpis["products_count"].val.text()),
                    (self.mp_kpis["avg_margin"].lbl.text(),
                     self.mp_kpis["avg_margin"].val.text()),
                    (self.mp_kpis["top_profit"].lbl.text(),
                     self.mp_kpis["top_profit"].val.text()),
                ],
            )

        if report_key == "best_selling":
            return ReportData(
                title=_t("rep_best_selling", lang),
                headers=[_t(h, lang) for h in
                         ["col_product", "col_category",
                          "col_qty", "col_sales", "col_inv_count"]],
                rows=self._table_to_rows(self.bs_table),
                kpis=[
                    (self.bs_kpis["total_qty"].lbl.text(),
                     self.bs_kpis["total_qty"].val.text()),
                    (self.bs_kpis["total_sales"].lbl.text(),
                     self.bs_kpis["total_sales"].val.text()),
                    (self.bs_kpis["top_qty"].lbl.text(),
                     self.bs_kpis["top_qty"].val.text()),
                    (self.bs_kpis["products_count"].lbl.text(),
                     self.bs_kpis["products_count"].val.text()),
                ],
            )

        return None

    def _table_to_rows(self, table: QTableWidget) -> list[list[str]]:
        rows = []
        for i in range(table.rowCount()):
            row = []
            for j in range(table.columnCount()):
                item = table.item(i, j)
                row.append(item.text() if item else "")
            rows.append(row)
        return rows

    def _on_export(self, report_key: str, fmt: str):
        report = self._get_report_data(report_key)
        if not report:
            QMessageBox.warning(
                self, _t("title", self.language),
                _t("export_no_data", self.language),
            )
            return
        if not report.rows:
            QMessageBox.warning(
                self, _t("title", self.language),
                _t("export_no_data", self.language),
            )
            return

        if fmt == "pdf":
            default_name = f"{report_key}_{date.today().isoformat()}.pdf"
            try:
                with TemporaryDirectory(prefix="costprofit-preview-") as temp_dir:
                    file_path = Path(temp_dir) / default_name
                    export_service.export_pdf(report, str(file_path))
                    show_pdf_preview(self, file_path, self.language, default_name)
            except Exception as e:
                QMessageBox.critical(
                    self, _t("title", self.language),
                    _t("export_err", self.language, err=str(e)),
                )
            return
        else:
            filter_str = "Excel (*.xlsx)"
            default_name = f"{report_key}_{date.today().isoformat()}.xlsx"
            dlg_title = _t("export_title_xls", self.language)

        file_path, _ = QFileDialog.getSaveFileName(
            self, dlg_title, default_name, filter_str,
        )
        if not file_path:
            return

        try:
            export_service.export_excel(report, file_path)

            QMessageBox.information(
                self, _t("title", self.language),
                _t("export_success", self.language, path=file_path),
            )
        except Exception as e:
            QMessageBox.critical(
                self, _t("title", self.language),
                _t("export_err", self.language, err=str(e)),
            )

    def reload_language(self, language):
        self.language = language
        self._reload_texts()
        self._switch_report(self.current_report)

    # --------------------------------------------------------
    # الأنماط
    # --------------------------------------------------------
    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; color: #FFFFFF; }
            QWidget#ReportsContent { background-color: #000000; }
            QWidget#ReportPane { background-color: #000000; }
            QFrame#ReportsSidebar {
                background-color: rgba(15, 29, 53, 0.7);
                border-right: 1px solid rgba(37, 99, 235, 0.2);
            }
            QLabel#ReportsSectionLabel {
                color: #60A5FA; font-size: 11px; font-weight: 700;
                letter-spacing: 1px;
                padding: 8px 8px 4px 8px;
                background: transparent;
            }
            QPushButton#ReportsNavBtn {
                background-color: transparent;
                color: rgba(203, 213, 225, 0.9);
                text-align: left;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px; font-weight: 500;
            }
            QPushButton#ReportsNavBtn:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #FFFFFF;
            }
            QPushButton#ReportsNavBtn[active="true"] {
                background-color: rgba(37, 99, 235, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
                font-weight: 600;
            }
            QFrame#HeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(37, 99, 235, 0.15),
                    stop:1 rgba(37, 99, 235, 0.02));
                border-bottom: 1px solid rgba(37, 99, 235, 0.25);
            }
            QLabel#PageTitle {
                color: #FFFFFF; font-size: 22px; font-weight: 700;
                background: transparent;
            }
            QLabel#PageSub {
                color: rgba(148,163,184,0.9); font-size: 13px;
                background: transparent;
            }
            QLabel#FieldLabel {
                color: rgba(148,163,184,0.9); font-size: 12px;
                background: transparent;
            }
            QLabel#CardTitle {
                color: #FFFFFF; font-size: 14px; font-weight: 600;
                background: transparent;
            }
            QFrame#Card {
                background-color: rgba(15, 29, 53, 0.7);
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 12px;
            }
            QFrame#KpiCard {
                background-color: rgba(15, 29, 53, 0.75);
                border: 1px solid rgba(37, 99, 235, 0.25);
                border-radius: 12px;
            }
            QLabel#KpiTitle {
                color: rgba(148,163,184,0.9);
                font-size: 11px;
                background: transparent;
            }
            QLabel#KpiValue {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 700;
                background: transparent;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: rgba(15, 29, 53, 0.9);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #2563EB;
            }
            QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background-color: rgba(15, 29, 53, 0.98);
                color: #FFFFFF;
                selection-background-color: #2563EB;
                border: 1px solid rgba(37, 99, 235, 0.5);
                border-radius: 8px;
            }
            QPushButton#ExportBtn {
                background-color: rgba(37, 99, 235, 0.15);
                color: #60A5FA;
                border: 1px solid rgba(37, 99, 235, 0.4);
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 14px;
            }
            QPushButton#ExportBtn:hover {
                background-color: rgba(37, 99, 235, 0.35);
                color: #FFFFFF;
                border: 1px solid rgba(59, 130, 246, 0.7);
            }
            QTableWidget {
                background-color: rgba(15, 29, 53, 0.5);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 10px;
                gridline-color: transparent;
                outline: none;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(37, 99, 235, 0.1);
            }
            QTableWidget::item:selected {
                background-color: rgba(37, 99, 235, 0.25);
            }
            QHeaderView::section {
                background-color: rgba(10, 22, 40, 0.9);
                color: rgba(148,163,184,0.95);
                border: none;
                border-bottom: 1px solid rgba(37, 99, 235, 0.3);
                padding: 8px 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QScrollBar:vertical {
                background: transparent; width: 10px; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(37, 99, 235, 0.4);
                border-radius: 5px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
