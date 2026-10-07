"""
صفحة لوحة التحكم (Dashboard).
"""
from PySide6.QtCore import Qt, QSize, Signal, QEvent, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QGridLayout, QSizePolicy,
)

from app.services.dashboard_service import dashboard_service
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.theme import set_widget_stylesheet


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "welcome_title":   ("Welcome back",                "مرحبًا بعودتك"),
    "welcome_sub":     ("Here's what's happening with your business.",
                        "إليك ما يحدث في نشاطك التجاري."),
    "kpi_invoices":    ("Total Invoices",              "إجمالي الفواتير"),
    "kpi_payments":    ("Total Payments",              "إجمالي المدفوعات"),
    "kpi_usd":         ("Total Value (USD)",           "القيمة بالدولار"),
    "kpi_profit":      ("Total Profit",                "إجمالي الأرباح"),
    "kpi_open":        ("Open Invoices",               "فواتير غير مؤرشفة"),
    "draft_title": ("Unarchived Invoices", "الفواتير غير المؤرشفة"),
    "table_supplier_invoice": ("Supplier Invoice No.", "رقم فاتورة المورد"),
    "table_qty": ("Total Quantity", "إجمالي الكمية"),
    "table_value": ("Total Value (USD)", "إجمالي القيمة بالدولار"),
    "recent_title":    ("🧾 Recent Invoices",          "🧾 أحدث الفواتير"),
    "qa_title":        ("⚡ Quick Actions",            "⚡ إجراءات سريعة"),
    "qa_invoice":      ("New Invoice",                 "فاتورة جديدة"),
    "qa_supplier":     ("Add Supplier",                "إضافة مورد"),
    "qa_product":      ("Add Product",                 "إضافة صنف"),
    "qa_reports":      ("Reports",                     "التقارير"),
    "alert_view":      ("View →",                      "عرض ←"),
    "alert_msg":       ("{n} draft invoice(s) not archived yet.",
                        "يوجد {n} فاتورة غير مؤرشفة."),
    "no_data":         ("No data for this period",     "لا توجد بيانات لهذه الفترة"),
    "no_invoices":     ("No invoices yet",             "لا توجد فواتير بعد"),
    "table_hash":      ("#",                           "#"),
    "table_supplier":  ("Supplier",                    "المورد"),
    "table_date":      ("Date",                        "التاريخ"),
    "table_usd":       ("USD",                         "دولار"),
    "table_profit":    ("Profit",                      "الربح"),
}


def _t(key, language, **kwargs):
    en, ar = TEXTS.get(key, ("", ""))
    text = ar if language == "ar" else en
    if kwargs:
        text = text.format(**kwargs)
    return text


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ============================================================
# الصفحة
# ============================================================
class DashboardPage(QWidget):

    # ✅ إشارة للتنقل بين الصفحات
    navigate_to = Signal(str)
    open_draft_requested = Signal(int)
    open_invoice_requested = Signal(int)

    def __init__(self, theme: str = "dark", language: str = "en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.period = "year"

        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self.refresh()

    # --------------------------------------------------------
    # البناء
    # --------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        set_widget_stylesheet(scroll, "QScrollArea { background: transparent; border: none; }")
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("DashboardContent")
        scroll.setWidget(content)

        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 24, 28, 28)
        self.main_layout.setSpacing(20)

        self._build_welcome_bar()
        self._build_kpis()
        self._build_draft_invoices()
        self._build_recent_invoices()
        self._build_quick_actions()

    # --------------------------------------------------------
    # Welcome Bar
    # --------------------------------------------------------
    def _build_welcome_bar(self):
        card = QFrame()
        card.setObjectName("WelcomeCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.welcome_title = QLabel("Welcome back")
        self.welcome_title.setObjectName("WelcomeTitle")
        text_col.addWidget(self.welcome_title)

        self.welcome_sub = QLabel("Here's what's happening with your business.")
        self.welcome_sub.setObjectName("WelcomeSub")
        text_col.addWidget(self.welcome_sub)

        layout.addLayout(text_col)
        layout.addStretch()

        self.period_combo = QComboBox()
        self._populate_period_combo()
        self.period_combo.currentIndexChanged.connect(self._on_period_change)
        layout.addWidget(self.period_combo)

        self.main_layout.addWidget(card)

    def _populate_period_combo(self):
        current = self.period_combo.currentData() if self.period_combo.count() else self.period
        self.period_combo.blockSignals(True)
        self.period_combo.clear()
        items = (
            [("This Year", "year"), ("This Quarter", "quarter"),
             ("This Month", "month"), ("This Week", "week"),
             ("Today", "today"), ("All Time", "all")]
            if self.language != "ar"
            else [("هذه السنة", "year"), ("هذا الربع", "quarter"),
                  ("هذا الشهر", "month"), ("هذا الأسبوع", "week"),
                  ("اليوم", "today"), ("كل الوقت", "all")]
        )
        for label, key in items:
            self.period_combo.addItem(label, key)
        for i in range(self.period_combo.count()):
            if self.period_combo.itemData(i) == current:
                self.period_combo.setCurrentIndex(i)
                break
        self.period_combo.blockSignals(False)

    # --------------------------------------------------------
    # Smart Alerts
    # --------------------------------------------------------


    # --------------------------------------------------------
    # KPI Cards
    # --------------------------------------------------------

    def _build_kpis(self):
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(16)
        self.kpi_cards = {}
        specs = [
            ("invoices_count", "receipt", "kpi_invoices", "#2563EB"),
            ("total_payments", "wallet", "kpi_payments", "#0EA5E9"),
            ("total_usd", "dollar", "kpi_usd", "#22C55E"),
            ("total_profit", "trending", "kpi_profit", "#F59E0B"),
        ]
        self._kpi_widgets = [self._make_kpi_card(*spec) for spec in specs]
        self.main_layout.addLayout(self.kpi_grid)
        self._layout_kpis()

    def _layout_kpis(self):
        columns = 4 if self.width() >= 1000 else 2 if self.width() >= 540 else 1
        while self.kpi_grid.count():
            self.kpi_grid.takeAt(0)
        for column in range(4):
            self.kpi_grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self._kpi_widgets):
            self.kpi_grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_kpi_widgets"):
            self._layout_kpis()

    def _make_kpi_card(self, key: str, icon_name: str, text_key: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("KpiCard")
        card.setMinimumHeight(120)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        r, g, b = _hex_to_rgb(color)

        icon_box = QLabel()
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFixedSize(56, 56)
        icon_box._theme_pixmap_icon = (icon_name, color, 28)
        icon_box.setPixmap(make_icon(icon_name, color=color if self.theme == "light" else "#FFFFFF", size=28).pixmap(28, 28))
        set_widget_stylesheet(icon_box, f"""
            QLabel {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0   rgba({r}, {g}, {b}, 0.55),
                    stop:0.5 rgba({r}, {g}, {b}, 0.30),
                    stop:1   rgba({r}, {g}, {b}, 0.15)
                );
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-top: 1px solid rgba(255, 255, 255, 0.45);
                border-radius: 16px;
            }}
        """)
        layout.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title = QLabel("")
        title.setObjectName("KpiTitle")
        text_col.addWidget(title)

        value = QLabel("—")
        value.setObjectName("KpiValue")
        text_col.addWidget(value)

        layout.addLayout(text_col)
        layout.addStretch()

        self.kpi_cards[key] = {
            "card": card, "title": title, "value": value,
            "color": color, "text_key": text_key, "icon_box": icon_box,
        }
        return card

    # --------------------------------------------------------
    # Recent Invoices
    # --------------------------------------------------------

    def _build_recent_invoices(self):
        self.recent_title, self.recent_table, self.recent_empty = self._build_invoice_list()
        self.recent_table.itemDoubleClicked.connect(
            lambda item: self.open_invoice_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))
        )

    def _build_draft_invoices(self):
        self.draft_title, self.draft_table, self.draft_empty = self._build_invoice_list()
        self.draft_table.itemDoubleClicked.connect(
            lambda item: self.open_draft_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))
        )

    def _build_invoice_list(self):
        card = QFrame()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        title = QLabel()
        title.setObjectName("CardTitle")
        layout.addWidget(title)
        table = QTableWidget(0, 4)
        table.verticalHeader().hide()
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setWordWrap(True)
        table.setTextElideMode(Qt.TextElideMode.ElideNone)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        table.viewport().installEventFilter(self)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table)
        empty = QLabel()
        empty.setObjectName("Muted")
        layout.addWidget(empty)
        self.main_layout.addWidget(card)
        return title, table, empty

    def _fill_invoice_list(self, table, empty, invoices):
        table.setRowCount(len(invoices))
        for index, invoice in enumerate(invoices):
            values = (
                invoice["supplier_name"], invoice.get("supplier_invoice_no") or "—",
                f'{invoice["total_qty"]:g}', f'$ {invoice["total_usd"]:,.2f}',
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setToolTip(str(value))
                item.setData(Qt.ItemDataRole.UserRole, invoice["id"])
                table.setItem(index, column, item)
            table.setRowHeight(index, 38)
        table.setVisible(bool(invoices))
        empty.setVisible(not invoices)
        empty.setText(_t("no_invoices", self.language))
        self._resize_invoice_list(table)

    def _resize_invoice_list(self, table):
        table.resizeRowsToContents()
        for index in range(table.rowCount()):
            table.setRowHeight(index, max(38, table.rowHeight(index)))
        height = table.horizontalHeader().sizeHint().height() + sum(table.rowHeight(index) for index in range(table.rowCount())) + 4
        if table.height() != height:
            table.setFixedHeight(height)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            for table in (getattr(self, "recent_table", None), getattr(self, "draft_table", None)):
                if table is not None and watched is table.viewport():
                    QTimer.singleShot(0, self, lambda table=table: self._resize_invoice_list(table))
                    break
        return super().eventFilter(watched, event)

    # --------------------------------------------------------
    # Quick Actions
    # --------------------------------------------------------
    def _build_quick_actions(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self.qa_title = QLabel("")
        self.qa_title.setObjectName("CardTitle")
        layout.addWidget(self.qa_title)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.qa_buttons: list[QPushButton] = []
        # ✅ (اسم الأيقونة، مفتاح النص، الصفحة المستهدفة)
        actions = [
            ("invoice",   "qa_invoice",  "invoice"),
            ("suppliers", "qa_supplier", "suppliers"),
            ("products",  "qa_product",  "products"),
            ("reports",   "qa_reports",  "reports"),
        ]

        for icon_name, text_key, target_page in actions:
            btn = QPushButton("")
            btn.setObjectName("QuickAction")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(56)
            btn.setIcon(make_icon(icon_name, color=self.palette_data["primary"], size=22))
            btn.setIconSize(QSize(22, 22))
            btn.setProperty("text_key", text_key)
            # ✅ عند الضغط → الانتقال إلى الصفحة
            btn.clicked.connect(
                lambda _, k=target_page: self.navigate_to.emit(k)
            )
            row.addWidget(btn, 1)
            self.qa_buttons.append(btn)

        layout.addLayout(row)
        self.main_layout.addWidget(card)

    # --------------------------------------------------------
    # تحديث النصوص
    # --------------------------------------------------------
    def _reload_texts(self):
        lang = self.language

        self.welcome_title.setText(_t("welcome_title", lang))
        self.welcome_sub.setText(_t("welcome_sub", lang))

        self.recent_title.setText(_t("recent_title", lang))
        self.qa_title.setText(_t("qa_title", lang))

        for key, data in self.kpi_cards.items():
            data["title"].setText(_t(data["text_key"], lang))

        for btn in self.qa_buttons:
            btn.setText(_t(btn.property("text_key"), lang))


        self.draft_title.setText(_t("draft_title", lang))
        headers = [_t(key, lang) for key in ("table_supplier", "table_supplier_invoice", "table_qty", "table_value")]
        self.recent_table.setHorizontalHeaderLabels(headers)
        self.draft_table.setHorizontalHeaderLabels(headers)
        self.recent_empty.setText(_t("no_invoices", lang))
        self.draft_empty.setText(_t("no_invoices", lang))

        self._populate_period_combo()

    # --------------------------------------------------------
    # تحديث البيانات
    # --------------------------------------------------------
    def refresh(self):
        kpis = dashboard_service.get_kpis(self.period)
        for key, value in kpis.items():
            if key in self.kpi_cards:
                v = self.kpi_cards[key]["value"]
                if key in ("total_payments", "total_profit"):
                    v.setText(f"{value:,.2f} د.ل")
                elif key == "total_usd":
                    v.setText(f"$ {value:,.2f}")
                else:
                    v.setText(f"{value:,}")

        self._fill_recent_table()
        self._fill_invoice_list(self.draft_table, self.draft_empty, dashboard_service.get_draft_invoices())


    def _fill_recent_table(self):
        self._fill_invoice_list(self.recent_table, self.recent_empty, dashboard_service.get_recent_invoices(limit=5))



    def _on_period_change(self):
        self.period = self.period_combo.currentData() or "year"
        self.refresh()

    def reload_language(self, language: str):
        self.language = language
        self._reload_texts()
        self.refresh()

    # --------------------------------------------------------
    # الأنماط
    # --------------------------------------------------------
    def _apply_style(self):
        c = self.palette_data
        set_widget_stylesheet(self, f"""
            QWidget#DashboardContent {{ background-color: #000000; }}
            QFrame#WelcomeCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(37, 99, 235, 0.18),
                    stop:1 rgba(37, 99, 235, 0.02)
                );
                border: 1px solid rgba(37, 99, 235, 0.35);
                border-radius: 14px;
            }}
            QLabel#WelcomeTitle {{ color: #FFFFFF; font-size: 20px; font-weight: 700; }}
            QLabel#WelcomeSub {{ color: rgba(148,163,184,0.9); font-size: 13px; }}
            QFrame#Card {{
                background-color: rgba(15, 29, 53, 0.75);
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 14px;
            }}
            QFrame#KpiCard {{
                background-color: rgba(15, 29, 53, 0.75);
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 14px;
            }}
            QLabel#KpiTitle {{ color: rgba(148,163,184,0.9); font-size: 13px; }}
            QLabel#KpiValue {{ color: #FFFFFF; font-size: 22px; font-weight: 700; }}
            QLabel#CardTitle {{ color: #FFFFFF; font-size: 16px; font-weight: 600; }}
            QFrame#AlertFrame {{
                background-color: rgba(245, 158, 11, 0.15);
                border: 1px solid rgba(245, 158, 11, 0.5);
                border-radius: 10px;
            }}
            QLabel#AlertIcon {{ color: #F59E0B; font-size: 20px; }}
            QLabel#AlertText {{ color: #F59E0B; font-size: 14px; font-weight: 500; }}
            QPushButton#AlertButton {{
                background-color: rgba(245, 158, 11, 0.2);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.5);
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton#AlertButton:hover {{ background-color: rgba(245, 158, 11, 0.3); }}
            QPushButton#QuickAction {{
                background-color: rgba(37, 99, 235, 0.12);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.35);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
                padding: 8px 16px;
            }}
            QPushButton#QuickAction:hover {{
                background-color: rgba(37, 99, 235, 0.25);
                border: 1px solid rgba(59, 130, 246, 0.7);
            }}
            QTableWidget {{
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid rgba(37, 99, 235, 0.15);
            }}
            QHeaderView::section {{
                background-color: transparent;
                color: rgba(148,163,184,0.8);
                border: none;
                border-bottom: 1px solid rgba(37, 99, 235, 0.3);
                padding: 8px;
                font-weight: 600;
                font-size: 12px;
            }}
            QComboBox {{
                background-color: rgba(15, 29, 53, 0.9);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.4);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                min-width: 140px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background-color: rgba(15, 29, 53, 0.98);
                color: #FFFFFF;
                selection-background-color: #2563EB;
                border: 1px solid rgba(37, 99, 235, 0.5);
                border-radius: 8px;
            }}
        """)