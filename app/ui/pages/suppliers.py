"""
صفحة إدارة الموردين.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QMessageBox, QTextEdit,
)

from app.services.supplier_service import supplier_service, SupplierError
from app.ui import PageControls
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.theme import set_widget_stylesheet


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "title":           ("Suppliers",                    "الموردون"),
    "subtitle":        ("Manage your suppliers and their contact information.",
                        "إدارة الموردين وبيانات الاتصال بهم."),
    "btn_new":         ("+ New Supplier",               "+ مورد جديد"),
    "btn_refresh":     ("Refresh",                      "تحديث"),
    "search_ph":       ("Search by name, code, phone, or email...",
                        "ابحث بالاسم، الكود، الهاتف، أو البريد..."),
    "sort_label":      ("Sort:",                        "ترتيب:"),
    "sort_newest":     ("Newest",                       "الأحدث"),
    "sort_oldest":     ("Oldest",                       "الأقدم"),
    "sort_name_asc":   ("Name A–Z",                     "الاسم أ–ي"),
    "sort_name_desc":  ("Name Z–A",                     "الاسم ي–أ"),
    "sort_most_p":     ("Most Products",                "الأكثر أصنافًا"),
    "sort_most_i":     ("Most Invoices",                "الأكثر فواتير"),
    "count":           ("{n} supplier(s)",              "{n} مورد"),
    "col_num":         ("#",                            "#"),
    "col_code":        ("Code",                         "الكود"),
    "col_name":        ("Name",                         "الاسم"),
    "col_phone":       ("Phone",                        "الهاتف"),
    "col_email":       ("Email",                        "البريد"),
    "col_products":    ("Products",                     "الأصناف"),
    "col_invoices":    ("Invoices",                     "الفواتير"),
    "col_actions":     ("Actions",                      "إجراءات"),
    "no_data":         ("No suppliers yet",             "لا يوجد موردون بعد"),
    "no_data_sub":     ("Click 'New Supplier' to add your first one.",
                        "اضغط على 'مورد جديد' لإضافة أول مورد."),
    "no_results":      ("No results found",             "لا نتائج"),
    "no_results_sub":  ("Try a different search term.", "جرّب كلمة بحث مختلفة."),
    # Dialog
    "dlg_new_title":   ("New Supplier",                 "مورد جديد"),
    "dlg_edit_title":  ("Edit Supplier",                "تعديل مورد"),
    "dlg_sub":         ("Add a new supplier to your system.",
                        "أضف موردًا جديدًا إلى نظامك."),
    "dlg_sub_edit":    ("Update supplier information.",
                        "حدّث بيانات المورد."),
    "field_code":      ("Supplier Code *",              "كود المورد *"),
    "field_name":      ("Supplier Name *",              "اسم المورد *"),
    "field_phone":     ("Phone",                        "الهاتف"),
    "field_email":     ("Email",                        "البريد الإلكتروني"),
    "field_address":   ("Address",                      "العنوان"),
    "auto_code":       ("Auto",                         "تلقائي"),
    "btn_cancel":      ("Cancel",                       "إلغاء"),
    "btn_save":        ("Save",                         "حفظ"),
    "btn_update":      ("Update",                       "تحديث"),
    # Details dialog
    "details_title":   ("Supplier Details",             "تفاصيل المورد"),
    "stat_products":   ("Products",                     "الأصناف"),
    "stat_invoices":   ("Invoices",                     "الفواتير"),
    "stat_payments":   ("Payments",                     "المدفوعات"),
    "stat_profit":     ("Profit",                       "الأرباح"),
    "btn_close":       ("Close",                        "إغلاق"),
    # Delete
    "confirm_delete_t": ("Delete Supplier",             "حذف المورد"),
    "confirm_delete_m": ("Are you sure you want to delete \"{name}\"?\nThis cannot be undone.",
                         "هل تريد حذف \"{name}\"؟\nلا يمكن التراجع."),
    "btn_delete":      ("Delete",                       "حذف"),
    # Errors
    "err_title":       ("Error",                        "خطأ"),
    "err_code_req":    ("Supplier code is required.",   "كود المورد مطلوب."),
    "err_name_req":    ("Supplier name is required.",   "اسم المورد مطلوب."),
    "err_code_exists": ("This supplier code already exists.",
                        "كود المورد موجود مسبقًا."),
    "err_has_links":   ("Cannot delete \"{name}\":\n{products} product(s), {invoices} invoice(s).",
                        "لا يمكن حذف \"{name}\":\n{products} صنف، {invoices} فاتورة."),
}


def _t(key: str, language: str, **kwargs) -> str:
    en, ar = TEXTS.get(key, ("", ""))
    text = ar if language == "ar" else en
    if kwargs:
        text = text.format(**kwargs)
    return text


# ============================================================
# نافذة الإضافة / التعديل
# ============================================================
class SupplierDialog(QDialog):

    def __init__(self, parent=None, language="en", theme="dark", supplier=None):
        super().__init__(parent)
        self.language = language
        self.theme = theme
        self.palette_data = get_palette(theme)
        self.supplier = supplier
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        is_edit = self.supplier is not None
        self.setWindowTitle(_t("dlg_edit_title" if is_edit else "dlg_new_title", self.language))
        self.setMinimumWidth(540)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel(_t("dlg_edit_title" if is_edit else "dlg_new_title", self.language))
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        sub = QLabel(_t("dlg_sub_edit" if is_edit else "dlg_sub", self.language))
        sub.setObjectName("DialogSub")
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setObjectName("Sep")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("S-001")
        code_row = QHBoxLayout()
        code_row.setSpacing(8)
        code_row.addWidget(self.code_input, 1)
        auto_btn = QPushButton(_t("auto_code", self.language))
        auto_btn.setObjectName("AutoBtn")
        auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        auto_btn.clicked.connect(self._on_auto_code)
        code_row.addWidget(auto_btn)
        code_widget = QWidget()
        code_widget.setLayout(code_row)
        form.addRow(_t("field_code", self.language), code_widget)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Al-Nour Co.")
        form.addRow(_t("field_name", self.language), self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("091-XXXXXXX")
        form.addRow(_t("field_phone", self.language), self.phone_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("supplier@example.com")
        form.addRow(_t("field_email", self.language), self.email_input)

        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("City, Street, Building...")
        self.address_input.setFixedHeight(80)
        form.addRow(_t("field_address", self.language), self.address_input)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(_t("btn_cancel", self.language))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(110)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton(
            _t("btn_update" if is_edit else "btn_save", self.language)
        )
        save_btn.setObjectName("PrimaryBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(140)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

        if is_edit:
            self.code_input.setText(self.supplier.get("code", ""))
            self.name_input.setText(self.supplier.get("name", ""))
            self.phone_input.setText(self.supplier.get("phone", "") or "")
            self.email_input.setText(self.supplier.get("email", "") or "")
            self.address_input.setPlainText(self.supplier.get("address", "") or "")
        else:
            self._on_auto_code()

        self.name_input.setFocus()

    def _on_auto_code(self):
        self.code_input.setText(supplier_service.generate_code())

    def _on_save(self):
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()

        if not code:
            QMessageBox.warning(self, _t("err_title", self.language),
                                _t("err_code_req", self.language))
            return
        if not name:
            QMessageBox.warning(self, _t("err_title", self.language),
                                _t("err_name_req", self.language))
            return

        try:
            if self.supplier is None:
                supplier_service.create(
                    code=code, name=name,
                    phone=self.phone_input.text(),
                    email=self.email_input.text(),
                    address=self.address_input.toPlainText(),
                )
            else:
                supplier_service.update(
                    self.supplier["id"], code=code, name=name,
                    phone=self.phone_input.text(),
                    email=self.email_input.text(),
                    address=self.address_input.toPlainText(),
                )
            self.accept()
        except SupplierError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QLabel#DialogTitle {
                color: #FFFFFF; font-size: 22px; font-weight: 700;
                background: transparent;
            }
            QLabel#DialogSub {
                color: rgba(148,163,184,0.9); font-size: 13px;
                background: transparent;
            }
            QFrame#Sep {
                background-color: rgba(37, 99, 235, 0.25);
                border: none;
            }
            QLabel {
                color: rgba(203, 213, 225, 0.9);
                font-size: 14px;
                background: transparent;
            }
            QLineEdit, QTextEdit {
                background-color: rgba(15, 29, 53, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #2563EB;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 18px;
            }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#PrimaryBtn:pressed { background-color: #1D4ED8; }
            QPushButton#SecondaryBtn {
                background-color: transparent;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                padding: 8px 18px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: rgba(255,255,255,0.05);
            }
            QPushButton#AutoBtn {
                background-color: rgba(37, 99, 235, 0.15);
                color: #60A5FA;
                border: 1px solid rgba(37, 99, 235, 0.4);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#AutoBtn:hover {
                background-color: rgba(37, 99, 235, 0.3);
            }
        """)


# ============================================================
# نافذة التفاصيل
# ============================================================
class SupplierDetailsDialog(QDialog):

    def __init__(self, parent=None, language="en", theme="dark", supplier=None):
        super().__init__(parent)
        self.language = language
        self.palette_data = get_palette(theme)
        self.supplier = supplier
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        s = self.supplier
        self.setWindowTitle(_t("details_title", self.language))
        self.setMinimumWidth(560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(s["name"])
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(f"{s['code']}")
        sub.setObjectName("DialogSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        info = QFrame()
        info.setObjectName("InfoBox")
        info_layout = QFormLayout(info)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(16, 14, 16, 14)

        info_layout.addRow("📞", QLabel(s.get("phone") or "—"))
        info_layout.addRow("✉", QLabel(s.get("email") or "—"))
        info_layout.addRow("📍", QLabel(s.get("address") or "—"))

        layout.addWidget(info)

        stats = supplier_service.get_stats(s["id"])

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        stat_specs = [
            ("stat_products", str(stats["products_count"]), "#2563EB"),
            ("stat_invoices", str(stats["invoices_count"]), "#22C55E"),
            ("stat_payments", f"{stats['total_payments']:,.0f} د.ل", "#0EA5E9"),
            ("stat_profit",   f"{stats['total_profit']:,.0f} د.ل",  "#F59E0B"),
        ]

        for key, value, color in stat_specs:
            box = QFrame()
            box.setObjectName("StatBox")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(14, 12, 14, 12)
            box_layout.setSpacing(4)

            lbl = QLabel(_t(key, self.language))
            lbl.setObjectName("StatLabel")
            box_layout.addWidget(lbl)

            val = QLabel(value)
            val.setObjectName("StatValue")
            set_widget_stylesheet(val, f"color: {color};")
            box_layout.addWidget(val)

            stats_row.addWidget(box, 1)

        layout.addLayout(stats_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(_t("btn_close", self.language))
        close_btn.setObjectName("PrimaryBtn")
        close_btn.setMinimumHeight(40)
        close_btn.setMinimumWidth(120)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QLabel#DialogTitle {
                color: #FFFFFF; font-size: 22px; font-weight: 700;
                background: transparent;
            }
            QLabel#DialogSub {
                color: rgba(148,163,184,0.9); font-size: 13px;
                background: transparent;
            }
            QLabel { color: #FFFFFF; font-size: 14px; background: transparent; }
            QFrame#InfoBox {
                background-color: rgba(15, 29, 53, 0.7);
                border: 1px solid rgba(37, 99, 235, 0.25);
                border-radius: 10px;
            }
            QFrame#StatBox {
                background-color: rgba(15, 29, 53, 0.7);
                border: 1px solid rgba(37, 99, 235, 0.25);
                border-radius: 10px;
            }
            QLabel#StatLabel {
                color: rgba(148,163,184,0.9); font-size: 11px;
                background: transparent;
            }
            QLabel#StatValue {
                font-size: 16px; font-weight: 700;
                background: transparent;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563EB; color: #FFFFFF;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
                padding: 8px 18px;
            }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
        """)


# ============================================================
# الصفحة الرئيسية
# ============================================================
class SuppliersPage(QWidget):

    ACTIONS_COL_WIDTH = 140  # عرض ثابت لعمود الإجراءات

    def __init__(self, theme: str = "dark", language: str = "en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self.refresh()

    # --------------------------------------------------------
    # البناء
    # --------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ===== Header =====
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(24, 18, 24, 18)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.title = QLabel("")
        self.title.setObjectName("PageTitle")
        text_col.addWidget(self.title)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("PageSub")
        text_col.addWidget(self.subtitle)
        header_layout.addLayout(text_col)
        header_layout.addStretch()

        self.new_btn = QPushButton("")
        self.new_btn.setObjectName("PrimaryBtn")
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setMinimumHeight(42)
        self.new_btn.setIcon(make_icon("suppliers", color="#FFFFFF", size=18))
        self.new_btn.setIconSize(QSize(18, 18))
        self.new_btn.clicked.connect(self._on_new)
        header_layout.addWidget(self.new_btn)

        layout.addWidget(header_card)

        # ===== Toolbar =====
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setMinimumHeight(40)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumHeight(40)
        self.sort_combo.setMinimumWidth(180)
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.sort_combo)

        self.refresh_btn = QPushButton("")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setIcon(make_icon("reports", color=(self.palette_data["primary"] if self.theme == "light" else "#FFFFFF"), size=16))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        layout.addLayout(toolbar)

        # ===== Counter =====
        self.counter = QLabel("")
        self.counter.setObjectName("CounterLabel")
        layout.addWidget(self.counter)

        # ===== Table =====
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setRowCount(0)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.pager = PageControls(self.refresh, self)
        layout.addWidget(self.pager)
        layout.addWidget(self.table, 1)

        # ===== Empty State =====
        self.empty_box = QFrame()
        self.empty_box.setObjectName("EmptyBox")
        empty_layout = QVBoxLayout(self.empty_box)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        empty_icon = QLabel()
        empty_icon.setPixmap(make_icon("suppliers", color="#2563EB", size=72).pixmap(72, 72))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        self.empty_title = QLabel("")
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)

        self.empty_sub = QLabel("")
        self.empty_sub.setObjectName("EmptySub")
        self.empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_sub)

        layout.addWidget(self.empty_box, 1)
        self.empty_box.setVisible(False)

    # --------------------------------------------------------
    # النصوص + رأس الجدول
    # --------------------------------------------------------
    def _reload_texts(self):
        lang = self.language
        self.title.setText(_t("title", lang))
        self.subtitle.setText(_t("subtitle", lang))
        self.new_btn.setText(_t("btn_new", lang))
        self.refresh_btn.setText(_t("btn_refresh", lang))
        self.search_input.setPlaceholderText(_t("search_ph", lang))

        current = self.sort_combo.currentData() if self.sort_combo.count() else "newest"
        self.sort_combo.blockSignals(True)
        self.sort_combo.clear()
        for key in ["newest", "oldest", "name_asc", "name_desc",
                    "most_products", "most_invoices"]:
            self.sort_combo.addItem(_t(f"sort_{key}", lang), key)
        for i in range(self.sort_combo.count()):
            if self.sort_combo.itemData(i) == current:
                self.sort_combo.setCurrentIndex(i)
                break
        self.sort_combo.blockSignals(False)

        headers = [
            _t("col_num", lang), _t("col_code", lang), _t("col_name", lang),
            _t("col_phone", lang), _t("col_email", lang),
            _t("col_products", lang), _t("col_invoices", lang),
            _t("col_actions", lang),
        ]
        self.table.setHorizontalHeaderLabels(headers)

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 90)
        self.table.setColumnWidth(7, self.ACTIONS_COL_WIDTH)

        self.empty_title.setText(_t("no_data", lang))
        self.empty_sub.setText(_t("no_data_sub", lang))

    # --------------------------------------------------------
    # البحث
    # --------------------------------------------------------
    def _on_search_changed(self):
        self.refresh()

    # --------------------------------------------------------
    # تحديث البيانات
    # --------------------------------------------------------
    def refresh(self):
        search = self.search_input.text().strip()
        sort = self.sort_combo.currentData() or "newest"

        filters = dict(search=search, sort=sort)
        total = supplier_service.get_all(**filters, count_only=True)
        self.pager.configure(filters, total, self.language)
        rows = supplier_service.get_all(**filters, limit=self.pager.size, offset=self.pager.offset)
        self.table.setRowCount(len(rows))
        self.counter.setText(_t("count", self.language, n=total))

        if not rows:
            self.table.setVisible(False)
            self.empty_box.setVisible(True)
            if search:
                self.empty_title.setText(_t("no_results", self.language))
                self.empty_sub.setText(_t("no_results_sub", self.language))
            else:
                self.empty_title.setText(_t("no_data", self.language))
                self.empty_sub.setText(_t("no_data_sub", self.language))
            return
        else:
            self.table.setVisible(True)
            self.empty_box.setVisible(False)

        for i, s in enumerate(rows):
            self._fill_row(i, s)

    def _fill_row(self, row_idx: int, s: dict):
        # #
        item = QTableWidgetItem(str(self.pager.offset + row_idx + 1))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 0, item)

        # Code
        code_item = QTableWidgetItem(s["code"])
        code_item.setData(Qt.ItemDataRole.UserRole, s["id"])
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 1, code_item)

        # Name
        self.table.setItem(row_idx, 2, QTableWidgetItem(s["name"]))

        # Phone
        self.table.setItem(row_idx, 3, QTableWidgetItem(s.get("phone") or "—"))

        # Email
        self.table.setItem(row_idx, 4, QTableWidgetItem(s.get("email") or "—"))

        # Products
        p_item = QTableWidgetItem(str(s["products_count"]))
        p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 5, p_item)

        # Invoices
        i_item = QTableWidgetItem(str(s["invoices_count"]))
        i_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 6, i_item)

        # Actions
        self.table.setCellWidget(row_idx, 7, self._make_actions_widget(s))

    def _make_actions_widget(self, s: dict) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(120)  # ← حد أدنى للعرض
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(6)  # ← مسافة واضحة
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # عرض
        view_btn = QPushButton("👁")
        view_btn.setObjectName("IconBtn")
        view_btn.setToolTip(_t("details_title", self.language))
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setFixedSize(34, 34)
        view_btn.clicked.connect(lambda: self._on_view(s))
        layout.addWidget(view_btn)

        # تعديل
        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("IconBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedSize(34, 34)
        edit_btn.clicked.connect(lambda: self._on_edit(s))
        layout.addWidget(edit_btn)

        # حذف
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("IconBtnDanger")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(34, 34)
        del_btn.clicked.connect(lambda: self._on_delete(s))
        layout.addWidget(del_btn)

        return w

    # --------------------------------------------------------
    # الأحداث
    # --------------------------------------------------------
    def _on_new(self):
        dlg = SupplierDialog(self, self.language, self.theme)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit(self, s: dict):
        dlg = SupplierDialog(self, self.language, self.theme, supplier=s)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_view(self, s: dict):
        dlg = SupplierDetailsDialog(self, self.language, self.theme, supplier=s)
        dlg.exec()

    def _on_delete(self, s: dict):
        stats = supplier_service.get_stats(s["id"])
        if stats["products_count"] > 0 or stats["invoices_count"] > 0:
            QMessageBox.warning(
                self,
                _t("err_title", self.language),
                _t("err_has_links", self.language,
                   name=s["name"],
                   products=stats["products_count"],
                   invoices=stats["invoices_count"]),
            )
            return

        reply = QMessageBox.question(
            self,
            _t("confirm_delete_t", self.language),
            _t("confirm_delete_m", self.language, name=s["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                supplier_service.delete(s["id"])
                self.refresh()
            except SupplierError as e:
                QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_row_double_clicked(self, item):
        row = item.row()
        code_item = self.table.item(row, 1)
        if not code_item:
            return
        sid = code_item.data(Qt.ItemDataRole.UserRole)
        s = supplier_service.get_by_id(sid)
        if s:
            self._on_view(s)

    def reload_language(self, language: str):
        self.language = language
        self._reload_texts()
        self.refresh()

    # --------------------------------------------------------
    # الأنماط
    # --------------------------------------------------------
    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; }
            QFrame#HeaderCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(37, 99, 235, 0.18),
                    stop:1 rgba(37, 99, 235, 0.02)
                );
                border: 1px solid rgba(37, 99, 235, 0.35);
                border-radius: 14px;
            }
            QLabel#PageTitle {
                color: #FFFFFF; font-size: 22px; font-weight: 700;
                background: transparent;
            }
            QLabel#PageSub {
                color: rgba(148,163,184,0.9); font-size: 13px;
                background: transparent;
            }
            QLabel#CounterLabel {
                color: rgba(148,163,184,0.85); font-size: 13px;
                background: transparent;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563EB; color: #FFFFFF;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
                padding: 8px 18px;
            }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn {
                background-color: rgba(15, 29, 53, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                font-size: 13px; font-weight: 500;
                padding: 8px 14px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: rgba(37, 99, 235, 0.15);
                border: 1px solid rgba(37, 99, 235, 0.5);
            }
            QLineEdit {
                background-color: rgba(15, 29, 53, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QComboBox {
                background-color: rgba(15, 29, 53, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: rgba(15, 29, 53, 0.98);
                color: #FFFFFF;
                selection-background-color: #2563EB;
                border: 1px solid rgba(37, 99, 235, 0.5);
                border-radius: 8px;
            }
            QTableWidget {
                background-color: rgba(15, 29, 53, 0.5);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 12px;
                gridline-color: transparent;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(37, 99, 235, 0.12);
            }
            QTableWidget::item:selected {
                background-color: rgba(37, 99, 235, 0.25);
            }
            QHeaderView::section {
                background-color: rgba(10, 22, 40, 0.9);
                color: rgba(148,163,184,0.9);
                border: none;
                border-bottom: 1px solid rgba(37, 99, 235, 0.3);
                padding: 10px 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#IconBtn {
                background-color: rgba(37, 99, 235, 0.15);
                color: #60A5FA;
                border: 1px solid rgba(37, 99, 235, 0.4);
                border-radius: 8px;
                font-size: 15px;
                padding: 0;
            }
            QPushButton#IconBtn:hover {
                background-color: rgba(37, 99, 235, 0.35);
                color: #FFFFFF;
                border: 1px solid rgba(59, 130, 246, 0.7);
            }
            QPushButton#IconBtnDanger {
                background-color: rgba(220, 38, 38, 0.15);
                color: #F87171;
                border: 1px solid rgba(220, 38, 38, 0.4);
                border-radius: 8px;
                font-size: 15px;
                padding: 0;
            }
            QPushButton#IconBtnDanger:hover {
                background-color: rgba(220, 38, 38, 0.35);
                color: #FFFFFF;
                border: 1px solid rgba(239, 68, 68, 0.7);
            }
            QFrame#EmptyBox {
                background-color: rgba(15, 29, 53, 0.4);
                border: 1px dashed rgba(37, 99, 235, 0.3);
                border-radius: 12px;
            }
            QLabel#EmptyTitle {
                color: #FFFFFF; font-size: 20px; font-weight: 600;
                background: transparent;
            }
            QLabel#EmptySub {
                color: rgba(148,163,184,0.85); font-size: 14px;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent; width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(37, 99, 235, 0.4);
                border-radius: 5px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(37, 99, 235, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
