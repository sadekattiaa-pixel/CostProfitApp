"""
النافذة الرئيسية — الهيكل العام (Shell).
"""
import sys
import ctypes
import time
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QTimer, QEvent
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QToolButton, QStatusBar, QMessageBox,
)

from app.config import APP_NAME, APP_VERSION, APP_AUTHOR
from app.services.settings_service import settings
from app.services.backup_service import backup_service
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.login_window import LoginWindow
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.suppliers import SuppliersPage
from app.ui.pages.products import ProductsPage
from app.ui.pages.invoice import InvoicePage
from app.ui.pages.archive import ArchivePage
from app.ui.pages.reports import ReportsPage
from app.ui.pages.settings import SettingsPage
from app.ui.import_invoice_dialog import ImportInvoiceDialog
from app.ui.theme import set_widget_stylesheet


NAV_ITEMS = [
    ("dashboard", "Dashboard", "لوحة التحكم"),
    ("suppliers", "Suppliers", "الموردون"),
    ("products",  "Products",  "الأصناف"),
    ("invoice",   "New Invoice", "فاتورة جديدة"),
    ("archive",   "Archive",   "الأرشيف"),
    ("reports",   "Reports",   "التقارير"),
    ("settings",  "Settings",  "الإعدادات"),
]


# ============================================================
# بيانات المطور
# ============================================================
DEVELOPER_NAME_EN = APP_AUTHOR
DEVELOPER_NAME_AR = "شركة الانطلاقة للبرمجة"
DEVELOPER_PERSON_EN = "Al-Siddiq Ben Attia"
DEVELOPER_PERSON_AR = "الصديق بن عطية"
DEVELOPER_PHONE = "00218915483857"
DEVELOPER_EMAIL = "Sadekattiaa@outlook.com"


def get_developer_logo_path() -> Path:
    """مسار شعار المطور."""
    app_root = Path(__file__).resolve().parents[2]
    return app_root / "assets" / "logo.png"


def enable_dark_title_bar(widget, enabled=True):
    """يجعل شريط عنوان النافذة داكنًا على Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(int(enabled))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.theme = settings.get("theme") or "dark"
        self.language = settings.get("language") or "en"
        self.palette_data = get_palette(self.theme)
        self.current_page = "dashboard"
        self.nav_buttons: dict[str, QPushButton] = {}
        self.dashboard_page: DashboardPage | None = None
        self.suppliers_page: SuppliersPage | None = None
        self.products_page: ProductsPage | None = None
        self.invoice_page: InvoicePage | None = None
        self.archive_page: ArchivePage | None = None
        self.reports_page: ReportsPage | None = None
        self.settings_page: SettingsPage | None = None

        self.placeholder_icons: dict[str, QLabel] = {}
        self.placeholder_titles: dict[str, QLabel] = {}
        self.placeholder_descs: dict[str, QLabel] = {}

        self._build_ui()
        self._apply_style()
        self._switch_page("dashboard")
        self._setup_auto_lock()
        self._setup_auto_backup()

        enable_dark_title_bar(self)

    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "app_icon.ico")))
        self.setMinimumSize(800, 560)
        self.resize(1400, 880)

        root = QWidget()
        self.setCentralWidget(root)
        self.root_layout = QHBoxLayout(root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()

        self.right_column = QWidget()
        right_layout = QVBoxLayout(self.right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.topbar = self._build_topbar()
        right_layout.addWidget(self.topbar)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentArea")

        for key, en, ar in NAV_ITEMS:
            if key == "dashboard":
                page = DashboardPage(theme=self.theme, language=self.language)
                self.dashboard_page = page
            elif key in ("suppliers", "products", "archive", "reports", "settings"):
                page = QWidget()
            elif key == "invoice":
                page = InvoicePage(theme=self.theme, language=self.language)
                self.invoice_page = page
            else:
                page = self._build_placeholder_page(key, en, ar)
            self.content_stack.addWidget(page)

        right_layout.addWidget(self.content_stack, 1)

        self.root_layout.addWidget(self.sidebar)
        self.root_layout.addWidget(self.right_column, 1)

        # إشارات Settings
        if self.settings_page:
            self.settings_page.language_changed.connect(self._on_settings_language_changed)
            self.settings_page.theme_changed.connect(self._on_settings_theme_changed)
            self.settings_page.backup_interval_changed.connect(self._on_backup_interval_changed)
            self.settings_page._pending_changes_guard = self.invoice_page.confirm_pending_changes

        # ✅ ربط إشارة التنقل من Dashboard
        if self.dashboard_page:
            self.dashboard_page.navigate_to.connect(self._switch_page)
            self.dashboard_page.open_draft_requested.connect(self._on_edit_draft_requested)
            self.dashboard_page.open_invoice_requested.connect(
                lambda invoice_id: self._ensure_page("archive")._on_view({"id": invoice_id})
            )

        # إشارة تعديل المسودة
        if self.archive_page:
            self.archive_page.edit_draft_requested.connect(self._on_edit_draft_requested)

        self._apply_layout_direction()
        self._build_statusbar()

    def _ensure_page(self, key):
        existing = getattr(self, key + "_page", None)
        if existing is not None:
            return existing
        classes = {"suppliers": SuppliersPage, "products": ProductsPage,
                   "archive": ArchivePage, "reports": ReportsPage, "settings": SettingsPage}
        if key not in classes:
            return None
        page = classes[key](theme=self.theme, language=self.language)
        setattr(self, key + "_page", page)
        index = [item[0] for item in NAV_ITEMS].index(key)
        placeholder = self.content_stack.widget(index)
        self.content_stack.removeWidget(placeholder)
        self.content_stack.insertWidget(index, page)
        placeholder.deleteLater()
        if key == "archive":
            page.edit_draft_requested.connect(self._on_edit_draft_requested)
        elif key == "settings":
            page.language_changed.connect(self._on_settings_language_changed)
            page.theme_changed.connect(self._on_settings_theme_changed)
            page.backup_interval_changed.connect(self._on_backup_interval_changed)
            page._pending_changes_guard = self.invoice_page.confirm_pending_changes
        return page

    def _on_edit_draft_requested(self, invoice_id: int):
        if self.invoice_page:
            self.invoice_page.load_invoice(invoice_id)
        self._switch_page("invoice")

    def showEvent(self, event):
        super().showEvent(event)
        self._last_activity = time.monotonic()
        QTimer.singleShot(0, self._update_responsive_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _update_responsive_layout(self):
        if not hasattr(self, "sidebar"):
            return
        collapsed = self.width() < 1180
        if getattr(self, "_sidebar_collapsed", None) == collapsed:
            return
        self._sidebar_collapsed = collapsed
        self.sidebar.setFixedWidth(84 if collapsed else 280)
        self.logo_banner.setFixedHeight(76 if collapsed else 140)
        self.dev_box.setVisible(not collapsed)
        for key, en, ar in NAV_ITEMS:
            btn = self.nav_buttons[key]
            label = ar if self.language == "ar" else en
            btn.setText("" if collapsed else f"  {label}")
            btn.setToolTip(label)
        self.lock_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if collapsed else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.lock_btn.setFixedWidth(44 if collapsed else 148)

    def _setup_auto_lock(self):
        self._last_activity = time.monotonic()
        self._auto_lock_timer = QTimer(self)
        self._auto_lock_timer.timeout.connect(self._check_auto_lock)
        self._auto_lock_timer.start(1_000)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _setup_auto_backup(self):
        self._auto_backup_timer = QTimer(self)
        self._auto_backup_timer.timeout.connect(self._create_auto_backup)
        minutes = max(1, settings.get_int("auto_backup_minutes", 30))
        self._auto_backup_timer.start(minutes * 60_000)

    def _on_backup_interval_changed(self, minutes):
        if hasattr(self, "_auto_backup_timer"):
            self._auto_backup_timer.setInterval(max(1, minutes) * 60_000)

    def _create_auto_backup(self):
        try:
            backup_service.create_backup(
                prefix="auto",
                keep=settings.get_int("backup_keep_count", 30),
            )
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
        ):
            self._last_activity = time.monotonic()
        return super().eventFilter(obj, event)

    def _check_auto_lock(self):
        if not self.isVisible():
            return
        minutes = settings.get_int("auto_lock_minutes", 10)
        if minutes > 0 and time.monotonic() - self._last_activity >= minutes * 60:
            self._on_lock()

    def _on_settings_language_changed(self, new_lang: str):
        if new_lang == self.language:
            return
        self.language = new_lang
        settings.set("language", new_lang)
        self.lang_btn.setText("AR" if self.language == "en" else "EN")

        for key, en, ar in NAV_ITEMS:
            label = ar if self.language == "ar" else en
            self.nav_buttons[key].setText(f"  {label}")

        self.lock_btn.setToolTip("قفل التطبيق" if self.language == "ar" else "Lock application")

        for key, en, ar in NAV_ITEMS:
            if key == self.current_page:
                self.page_title.setText(ar if self.language == "ar" else en)
                break

        if self.dashboard_page:
            self.dashboard_page.reload_language(self.language)
        if self.suppliers_page:
            self.suppliers_page.reload_language(self.language)
        if self.products_page:
            self.products_page.reload_language(self.language)
        if self.invoice_page:
            self.invoice_page.reload_language(self.language)
        if self.archive_page:
            self.archive_page.reload_language(self.language)
        if self.reports_page:
            self.reports_page.reload_language(self.language)
        if self.settings_page:
            self.settings_page.language = self.language

        self._update_dev_info_text()
        if hasattr(self, "save_status_label"):self.update_save_status(self._save_state, self._save_error)
        self._apply_layout_direction()

    def _on_settings_theme_changed(self, new_theme: str):
        if new_theme == self.theme:
            return
        self.theme = new_theme
        settings.set("theme", new_theme)
        self.theme_btn.setText("☀" if self.theme == "dark" else "🌙")
        from PySide6.QtWidgets import QApplication
        from app.ui.theme import apply_theme
        app = QApplication.instance()
        apply_theme(app, self.theme)

        enable_dark_title_bar(self)

    def _apply_layout_direction(self):
        if self.language == "ar":
            direction = Qt.LayoutDirection.RightToLeft
        else:
            direction = Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(direction)
        self._apply_style()

    # ============================================================
    # السايد بار
    # ============================================================
    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # بانر الشعار
        self.logo_banner = QLabel()
        self.logo_banner.setObjectName("SidebarLogoBanner")
        self.logo_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_banner.setFixedHeight(140)
        self.logo_banner.setScaledContents(False)
        self._load_logo_banner()
        layout.addWidget(self.logo_banner)

        # المحتوى
        content = QWidget()
        content.setObjectName("SidebarContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 22, 16, 18)
        content_layout.setSpacing(8)

        for key, en, ar in NAV_ITEMS:
            label = ar if self.language == "ar" else en
            btn = QPushButton(f"  {label}")
            btn.setObjectName("NavButton")
            btn.setProperty("active", False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(52)
            btn.setIconSize(QSize(26, 26))
            btn.setCheckable(True)
            btn.setIcon(make_icon(key, color=get_palette("dark")["text_muted"], size=26))
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            self.nav_buttons[key] = btn
            content_layout.addWidget(btn)

        content_layout.addStretch()

        divider0 = QFrame()
        divider0.setFixedHeight(1)
        divider0.setObjectName("Divider")
        content_layout.addWidget(divider0)
        content_layout.addSpacing(6)

        # بيانات المطور
        self.dev_box = QFrame()
        self.dev_box.setObjectName("DevInfoBox")
        self.dev_box.setMinimumHeight(132)
        dl = QVBoxLayout(self.dev_box)
        dl.setContentsMargins(12, 12, 12, 12)
        dl.setSpacing(4)

        self.dev_name_lbl = QLabel()
        self.dev_name_lbl.setObjectName("DevName")
        self.dev_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dev_name_lbl.setWordWrap(True)
        dl.addWidget(self.dev_name_lbl)

        self.dev_company_lbl = QLabel()
        self.dev_company_lbl.setObjectName("DevCompany")
        self.dev_company_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dev_company_lbl.setWordWrap(True)
        dl.addWidget(self.dev_company_lbl)

        self.dev_phone_lbl = QLabel()
        self.dev_phone_lbl.setObjectName("DevContact")
        self.dev_phone_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dev_phone_lbl.setWordWrap(True)
        dl.addWidget(self.dev_phone_lbl)

        self.dev_email_lbl = QLabel()
        self.dev_email_lbl.setObjectName("DevContact")
        self.dev_email_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dev_email_lbl.setWordWrap(True)
        dl.addWidget(self.dev_email_lbl)

        content_layout.addWidget(self.dev_box)
        content_layout.addSpacing(6)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setObjectName("Divider")
        content_layout.addWidget(divider)

        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("SidebarVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(version)

        layout.addWidget(content, 1)

        self._update_dev_info_text()
        return sidebar

    def _load_logo_banner(self):
        """يحمّل شعار المطور لبانر السايد بار."""
        logo_path = get_developer_logo_path()
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                self.logo_banner.setPixmap(
                    pix.scaled(
                        280, 140,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.logo_banner.setText("Alintilqa")
        set_widget_stylesheet(self.logo_banner, "color: #FFFFFF; font-size: 26px; font-weight: 800; "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #3B82F6, stop:1 #1D4ED8); "
            "border-bottom: 1px solid rgba(37, 99, 235, 0.3);")

    def _update_dev_info_text(self):
        """Keep the developer's identity unchanged across languages."""
        self.dev_name_lbl.setText(DEVELOPER_PERSON_AR)
        self.dev_company_lbl.setText(DEVELOPER_NAME_AR)
        self.dev_phone_lbl.setText(f"📞 {DEVELOPER_PHONE}")
        self.dev_email_lbl.setText(f"✉ {DEVELOPER_EMAIL}")

    # ============================================================
    # الشريط العلوي
    # ============================================================
    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(68)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(12)

        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        layout.addWidget(self.page_title)
        layout.addStretch()

        self.lang_btn = QToolButton()
        self.lang_btn.setText("AR" if self.language == "en" else "EN")
        self.lang_btn.setObjectName("TopbarButton")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setToolTip("Switch language")
        self.lang_btn.clicked.connect(self._toggle_language)
        layout.addWidget(self.lang_btn)

        self.theme_btn = QToolButton()
        self.theme_btn.setText("☀" if self.theme == "dark" else "🌙")
        self.theme_btn.setObjectName("TopbarButton")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Toggle theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)

        self.import_btn = QToolButton()
        self.import_btn.setText("📥")
        self.import_btn.setObjectName("TopbarButton")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setToolTip("Import invoices from Excel")
        self.import_btn.clicked.connect(self._open_excel_import_dialog)
        layout.addWidget(self.import_btn)

        self.lock_btn = QToolButton()
        self.lock_btn.setObjectName("TopbarButton")
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setFixedWidth(148)
        self.lock_btn.setMinimumHeight(38)
        self.lock_btn.setIcon(make_icon("lock", color=self.palette_data["text_muted"], size=20))
        self.lock_btn.setIconSize(QSize(20, 20))
        self.lock_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.lock_btn.setText("قفل" if self.language == "ar" else "Lock")
        self.lock_btn.setAccessibleName("قفل التطبيق" if self.language == "ar" else "Lock application")
        self.lock_btn.setToolTip("قفل التطبيق" if self.language == "ar" else "Lock application")
        self.lock_btn.clicked.connect(self._on_lock)
        layout.addWidget(self.lock_btn)

        return topbar

    def _build_placeholder_page(self, key: str, en: str, ar: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(
            make_icon(key, color=self.palette_data["primary"], size=96).pixmap(96, 96)
        )
        layout.addWidget(icon_label)
        self.placeholder_icons[key] = icon_label

        title = QLabel(ar if self.language == "ar" else en)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PlaceholderTitle")
        layout.addWidget(title)
        self.placeholder_titles[key] = title

        desc = QLabel(self._make_placeholder_desc(en, ar))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setObjectName("PlaceholderDesc")
        layout.addWidget(desc)
        self.placeholder_descs[key] = desc

        return page

    def _make_placeholder_desc(self, en: str, ar: str) -> str:
        label = ar if self.language == "ar" else en
        if self.language == "ar":
            return f"صفحة '{label}' قيد الإنشاء"
        return f"'{label}' page is under construction"

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.save_status_label = QLabel()
        sb.addWidget(self.save_status_label, 1)
        self._save_state, self._save_error = "saving", ""
        self.update_save_status(self._save_state)

    def update_save_status(self, state, error=""):
        self._save_state, self._save_error = state, error
        names = {"saved": ("تم الحفظ", "Saved", "#22C55E"), "saving": ("جاري الحفظ", "Saving", "#EAB308"), "failed": ("لم يتم الحفظ", "Not saved", "#EF4444")}
        ar, en, color = names.get(state, names["failed"])
        self.save_status_label.setText(f'<span style="color:{color};font-size:18px">●</span> {ar if self.language == "ar" else en}')
        from app.paths import get_shared_db_path
        self.save_status_label.setToolTip(error or str(get_shared_db_path().parent))


    def _switch_page(self, key: str):
        keys = [item[0] for item in NAV_ITEMS]
        if key not in keys:
            return
        index = keys.index(key)
        self._ensure_page(key)
        self.content_stack.setCurrentIndex(index)

        for k, btn in self.nav_buttons.items():
            active = (k == key)
            btn.setProperty("active", active)
            btn.setChecked(active)
            color = get_palette("dark")["primary"] if active else get_palette("dark")["text_muted"]
            btn.setIcon(make_icon(k, color=color, size=26))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        item = NAV_ITEMS[index]
        self.page_title.setText(item[2] if self.language == "ar" else item[1])
        self.current_page = key

        if key == "dashboard" and self.dashboard_page:
            self.dashboard_page.refresh()
        elif key == "suppliers" and self.suppliers_page:
            self.suppliers_page.refresh()
        elif key == "products" and self.products_page:
            self.products_page.refresh()
        elif key == "invoice" and self.invoice_page:
            self.invoice_page._reload_suppliers()
            if self.invoice_page.invoice_id is None:
                from app.services.invoice_service import invoice_service
                self.invoice_page.inv_no_input.setText(invoice_service.generate_invoice_number())
        elif key == "archive" and self.archive_page:
            self.archive_page.refresh()
        elif key == "reports" and self.reports_page:
            self.reports_page._switch_report(self.reports_page.current_report)
        elif key == "settings" and self.settings_page:
            self.settings_page._switch_section(self.settings_page.current_section)

    def _toggle_language(self):
        self.language = "ar" if self.language == "en" else "en"
        settings.set("language", self.language)
        self.lang_btn.setText("AR" if self.language == "en" else "EN")

        for key, en, ar in NAV_ITEMS:
            label = ar if self.language == "ar" else en
            self.nav_buttons[key].setText(
                "" if getattr(self, "_sidebar_collapsed", False) else f"  {label}"
            )

        self.lock_btn.setText("قفل" if self.language == "ar" else "Lock")
        self.lock_btn.setAccessibleName("قفل التطبيق" if self.language == "ar" else "Lock application")
        self.lock_btn.setToolTip("قفل التطبيق" if self.language == "ar" else "Lock application")

        for key, en, ar in NAV_ITEMS:
            if key == self.current_page:
                self.page_title.setText(ar if self.language == "ar" else en)
                break

        for key, en, ar in NAV_ITEMS:
            if key in self.placeholder_titles:
                self.placeholder_titles[key].setText(ar if self.language == "ar" else en)
            if key in self.placeholder_descs:
                self.placeholder_descs[key].setText(self._make_placeholder_desc(en, ar))

        if self.dashboard_page:
            self.dashboard_page.reload_language(self.language)
        if self.suppliers_page:
            self.suppliers_page.reload_language(self.language)
        if self.products_page:
            self.products_page.reload_language(self.language)
        if self.invoice_page:
            self.invoice_page.reload_language(self.language)
        if self.archive_page:
            self.archive_page.reload_language(self.language)
        if self.reports_page:
            self.reports_page.reload_language(self.language)
        if self.settings_page:
            self.settings_page.language = self.language
            self.settings_page._reload_texts()

        self._update_dev_info_text()
        if hasattr(self, "save_status_label"):self.update_save_status(self._save_state, self._save_error)
        self._apply_layout_direction()

    def _toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        settings.set("theme", self.theme)
        self.theme_btn.setText("☀" if self.theme == "dark" else "🌙")
        from PySide6.QtWidgets import QApplication
        from app.ui.theme import apply_theme
        app = QApplication.instance()
        apply_theme(app, self.theme)

        enable_dark_title_bar(self)

    def _open_excel_import_dialog(self):
        dialog = ImportInvoiceDialog(self, theme=self.theme)
        dialog.exec()

    def _on_lock(self):
        if not self.isVisible():
            return
        self._last_activity = time.monotonic()
        self.hide()
        login = LoginWindow()
        login._close_guard = self.invoice_page.confirm_pending_changes
        login.setWindowModality(Qt.WindowModality.ApplicationModal)

        def on_login_success():
            login._close_guard = None
            login.close()
            self._last_activity = time.monotonic()
            self.show()

        login.login_successful.connect(on_login_success)
        login.show()

    def closeEvent(self, event):
        if self.invoice_page and not self.invoice_page.confirm_pending_changes():
            event.ignore()
            return
        self._create_auto_backup()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        if hasattr(self, "_auto_lock_timer"):
            self._auto_lock_timer.stop()
        if hasattr(self, "_auto_backup_timer"):
            self._auto_backup_timer.stop()
        super().closeEvent(event)

    def _apply_style(self):
        c = self.palette_data

        if self.language == "ar":
            sidebar_border = "border-left: 1px solid rgba(37, 99, 235, 0.25); border-right: none;"
        else:
            sidebar_border = "border-right: 1px solid rgba(37, 99, 235, 0.25); border-left: none;"

        set_widget_stylesheet(self, f"""
            QFrame#Sidebar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0.4, y2:1,
                    stop:0    rgba(20, 38, 68, 0.98),
                    stop:0.5  rgba(12, 24, 45, 0.96),
                    stop:1    rgba(18, 34, 62, 0.98)
                );
                {sidebar_border}
            }}
            QWidget#SidebarContent {{
                background: transparent;
            }}
            QLabel#SidebarLogoBanner {{
                background-color: rgba(10, 22, 40, 0.7);
                border-bottom: 1px solid rgba(37, 99, 235, 0.35);
                padding: 0;
                margin: 0;
            }}
            QLabel#SidebarVersion {{
                color: rgba(148, 163, 184, 0.6);
                font-size: 12px;
                padding-top: 8px;
                letter-spacing: 0.5px;
            }}
            QFrame#DevInfoBox {{
                background-color: rgba(37, 99, 235, 0.08);
                border: 1px solid rgba(37, 99, 235, 0.25);
                border-radius: 10px;
            }}
            QLabel#DevName {{
                color: #60A5FA;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 0.3px;
                background: transparent;
            }}
            QLabel#DevCompany {{
                color: rgba(203, 213, 225, 0.82);
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }}
            QLabel#DevContact {{
                color: rgba(148, 163, 184, 0.85);
                font-size: 11px;
                background: transparent;
            }}
            QFrame#Divider {{
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                margin: 4px 2px;
            }}
            QPushButton#NavButton {{
                background-color: rgba(255, 255, 255, 0.025);
                color: rgba(203, 213, 225, 0.9);
                text-align: left;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 18px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }}
            QPushButton#NavButton:hover {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }}
            QPushButton#NavButton[active="true"] {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0   rgba(37, 99, 235, 0.35),
                    stop:0.6 rgba(37, 99, 235, 0.18),
                    stop:1   rgba(37, 99, 235, 0.05)
                );
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
                font-weight: 700;
            }}
            QFrame#Topbar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 29, 53, 0.98),
                    stop:1 rgba(10, 22, 40, 0.98)
                );
                border-bottom: 1px solid rgba(37, 99, 235, 0.2);
            }}
            QLabel#PageTitle {{
                color: #FFFFFF;
                font-size: 22px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            QToolButton#TopbarButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 15px;
                font-weight: 600;
                min-width: 42px;
                min-height: 38px;
            }}
            QToolButton#TopbarButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.5);
            }}
            QWidget#ContentArea {{
                background-color: #000000;
            }}
            QLabel#PlaceholderTitle {{
                color: #FFFFFF;
                font-size: 28px;
                font-weight: 700;
            }}
            QLabel#PlaceholderDesc {{
                color: rgba(148, 163, 184, 0.9);
                font-size: 16px;
            }}
            QStatusBar {{
                background-color: rgba(15, 29, 53, 0.95);
                color: rgba(148, 163, 184, 0.9);
                border-top: 1px solid rgba(37, 99, 235, 0.15);
                padding: 6px 14px;
                font-size: 13px;
            }}
        """)
        if hasattr(self, "lock_btn"):
            self.lock_btn.setFixedWidth(
                44 if getattr(self, "_sidebar_collapsed", False) else 148
            )
