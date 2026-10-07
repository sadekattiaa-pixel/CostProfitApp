"""
صفحة الإعدادات — 7 أقسام مع لوحة جانبية.
"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QScrollArea, QStackedWidget,
    QMessageBox, QFileDialog, QCheckBox, QGridLayout, QSpinBox, QTextEdit,
    QDialog, QFormLayout, QDialogButtonBox, QSizePolicy, QApplication, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
)

from app.config import APP_NAME, APP_VERSION, APP_AUTHOR
from app.services.settings_service import settings
from app.services.product_service import product_service, ProductError
from app.services.auth_service import auth, AuthError
from app.paths import (
    get_default_data_dir, get_db_path, get_company_dir,
    get_images_dir, get_backups_dir, get_auto_backups_dir,
)
from app.storage_config import RESTART_EXIT_CODE, update_storage_config, validate_backup_dir
from app.services.backup_service import backup_service
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.theme import set_widget_stylesheet


# ============================================================
# الترجمات
# ============================================================
TEXTS = {
    "title":         ("Settings",                    "الإعدادات"),
    "subtitle":      ("Manage your application preferences.",
                      "إدارة تفضيلات التطبيق."),

    # Sections
    "sec_general":   ("General",                     "عام"),
    "sec_company":   ("Company",                     "الشركة"),
    "sec_security":  ("Security",                    "الأمان"),
    "sec_backup":    ("Backup",                      "النسخ الاحتياطي"),
    "sec_invoice":   ("Invoice",                     "الفاتورة"),
    "sec_images": ("Images", "الصور"),
    "sec_about":     ("About",                       "حول البرنامج"),
    "sec_danger":    ("Danger Zone",                 "منطقة الخطر"),

    # General
    "language":      ("Language",                    "اللغة"),
    "english":       ("English",                     "الإنجليزية"),
    "arabic":        ("Arabic",                      "العربية"),
    "theme":         ("Theme",                       "الوضع"),
    "dark":          ("Dark",                        "ليلي"),
    "light":         ("Light",                       "نهاري"),
    "date_format":   ("Date Format",                 "صيغة التاريخ"),

    # Company
    "company_logo":     ("Company Logo",             "شعار الشركة"),
    "upload_logo":      ("Upload Logo",              "رفع شعار"),
    "remove_logo":      ("Remove",                   "حذف"),
    "no_logo":          ("No logo",                  "لا يوجد شعار"),
    "logo_hint":        ("PNG/JPG, max 2 MB",        "PNG/JPG، حد أقصى 2 MB"),
    "company_name":     ("Company Name",             "اسم الشركة"),
    "company_address":  ("Address",                  "العنوان"),
    "company_phone":    ("Phone",                    "الهاتف"),
    "company_email":    ("Email",                    "البريد الإلكتروني"),
    "company_website":  ("Website",                  "الموقع الإلكتروني"),
    "btn_save":         ("Save",                     "حفظ"),
    "saved":            ("Saved successfully.",      "تم الحفظ بنجاح."),

    # Security
    "change_password":    ("Change Password",        "تغيير كلمة المرور"),
    "current_password":   ("Current Password",       "كلمة المرور الحالية"),
    "new_password":       ("New Password",           "كلمة المرور الجديدة"),
    "confirm_password":   ("Confirm New Password",   "تأكيد كلمة المرور"),
    "update_password":    ("Update Password",        "تحديث كلمة المرور"),
    "auto_lock":          ("Auto-Lock",              "القفل التلقائي"),
    "auto_lock_after":    ("Lock after inactivity:", "القفل بعد الخمول:"),
    "minutes":            ("minutes",                "دقائق"),
    "never":              ("Never",                  "أبدًا"),

    # Backup
    "backup_location":    ("Backup Folder",          "مجلد النسخ الاحتياطي"),
    "data_folder":        ("Data and Images Folder", "مجلد البيانات والصور"),
    "change_folder":      ("Change Folder",          "تغيير المجلد"),
    "open_folder":        ("Open Folder",            "فتح المجلد"),
    "create_backup":      ("Create Backup Now",      "إنشاء نسخة الآن"),
    "backup_history":     ("Backup History",         "سجل النسخ الاحتياطية"),
    "col_date":           ("Date",                   "التاريخ"),
    "col_size":           ("Size",                   "الحجم"),
    "col_actions":        ("Actions",                "إجراءات"),
    "restore":            ("Restore",                "استعادة"),
    "delete":             ("Delete",                 "حذف"),
    "no_backups":         ("No backups yet",         "لا توجد نسخ احتياطية بعد"),
    "backup_created":     ("Backup created:\n{path}", "تم إنشاء النسخة:\n{path}"),
    "confirm_restore":    ("Restore this backup?\nCurrent data will be replaced.",
                           "استعادة هذه النسخة؟\nسيتم استبدال البيانات الحالية."),
    "restore_done":       ("Restored. Please restart the app.",
                           "تمت الاستعادة. يرجى إعادة تشغيل البرنامج."),
    "confirm_delete_bk":  ("Delete this backup?",    "حذف هذه النسخة؟"),
    "restart_storage":    ("Storage location changed. The application will restart now.",
                           "تم تغيير موقع التخزين. سيُعاد تشغيل البرنامج الآن."),
    "backup_interval":    ("Automatic backup interval (minutes)", "فترة النسخ التلقائي (دقائق)"),
    "backup_keep":        ("Number of backups to keep", "عدد النسخ المحتفظ بها"),

    # Invoice
    "default_prefix":     ("Invoice Prefix",         "بادئة رقم الفاتورة"),
    "next_invoice_no":    ("Next Invoice Number",    "رقم الفاتورة التالي"),

    # About
    "app_name":           ("Application",            "التطبيق"),
    "version":            ("Version",                "الإصدار"),
    "author":             ("Author",                 "المطوّر"),
    "data_location":      ("Data Location",          "موقع البيانات"),
    "db_size":            ("Database Size",          "حجم قاعدة البيانات"),

    # Danger
    "danger_warning":     ("⚠ These actions are permanent and cannot be undone.",
                           "⚠ هذه الإجراءات نهائية ولا يمكن التراجع عنها."),
    "reset_app":          ("Reset Application",      "إعادة تعيين البرنامج"),
    "reset_desc":         ("Delete all data and restore factory settings.",
                           "حذف كل البيانات واستعادة الإعدادات الافتراضية."),
    "confirm_reset":      ("This will DELETE ALL DATA permanently.\nType DELETE to confirm:",
                           "سيتم حذف كل البيانات نهائيًا.\nاكتب DELETE للتأكيد:"),
    "reset_done":         ("Application reset. The app will close; please reopen it.",
                           "تمت إعادة التعيين. سيُغلق البرنامج؛ يرجى فتحه مجددًا."),

    # Common
    "err_title":          ("Error",                  "خطأ"),
    "info_title":         ("Information",            "معلومة"),
    "confirm_title":      ("Confirm",                "تأكيد"),
}


def _t(key, language, **kwargs):
    en, ar = TEXTS.get(key, ("", ""))
    text = ar if language == "ar" else en
    if kwargs:
        text = text.format(**kwargs)
    return text


def _fmt_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


# ============================================================
# الصفحة الرئيسية
# ============================================================
class _NotesCardEditor(QTextEdit):
    """Expand the settings card to show all note text without scrolling."""
    def __init__(self):
        super().__init__()
        self.setObjectName("InvoiceNotesEditor")
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().documentLayout().documentSizeChanged.connect(self._fit_height)
        self.textChanged.connect(self._fit_height)
        self.setMinimumHeight(70)

    def _fit_height(self, *_):
        import math
        height = math.ceil(self.document().documentLayout().documentSize().height())
        padding = self.height() - self.viewport().height()
        target = max(70, height + max(2, padding) + 4)
        if self.height() != target:
            self.setFixedHeight(target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._fit_height)


class SettingsPage(QWidget):

    # إشارات للتواصل مع MainWindow
    language_changed = Signal(str)
    theme_changed = Signal(str)

    def __init__(self, theme="dark", language="en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.current_section = "general"
        self._logo_changed = False

        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self._switch_section("general")

    # --------------------------------------------------------
    # البناء
    # --------------------------------------------------------
    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(240)
        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(16, 20, 16, 20)
        sl.setSpacing(6)

        self.sidebar_buttons = {}
        sections = [
            ("general", "sec_general"),
            ("company", "sec_company"),
            ("security", "sec_security"),
            ("backup", "sec_backup"),
            ("invoice", "sec_invoice"),
            ("images", "sec_images"),
            ("about", "sec_about"),
            ("danger", "sec_danger"),
        ]

        for key, text_key in sections:
            btn = QPushButton("")
            btn.setObjectName("SettingsNavBtn")
            btn.setProperty("active", False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.setCheckable(True)
            btn.setProperty("section_key", key)
            btn.setProperty("text_key", text_key)
            btn.clicked.connect(lambda _, k=key: self._switch_section(k))
            self.sidebar_buttons[key] = btn
            sl.addWidget(btn)

        sl.addStretch()
        outer.addWidget(self.sidebar)

        # Content
        right_col = QWidget()
        right_col.setObjectName("SettingsContent")
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
        self.stack.setObjectName("SettingsStack")

        self.section_general = self._build_general()
        self.section_company = self._build_company()
        self.section_security = self._build_security()
        self.section_backup = self._build_backup()
        self.section_invoice = self._build_invoice()
        self.section_images = self._build_images()
        self.section_about = self._build_about()
        self.section_danger = self._build_danger()

        self.stack.addWidget(self.section_general)
        self.stack.addWidget(self.section_company)
        self.stack.addWidget(self.section_security)
        self.stack.addWidget(self.section_backup)
        self.stack.addWidget(self.section_invoice)
        self.stack.addWidget(self.section_images)
        self.stack.addWidget(self.section_about)
        self.stack.addWidget(self.section_danger)

        rl.addWidget(self.stack, 1)
        outer.addWidget(right_col, 1)

    # --------------------------------------------------------
    # Helper: بطاقة قسم
    # --------------------------------------------------------
    def _make_card(self, title_text=""):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        if title_text:
            lbl = QLabel(title_text)
            lbl.setObjectName("CardTitle")
            layout.addWidget(lbl)
        return card, layout

    def _make_field_label(self, text=""):
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    # --------------------------------------------------------
    # 1) General
    # --------------------------------------------------------
    def _build_general(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        w.setObjectName("SectionPane")
        scroll.setWidget(w)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Language
        card, cl = self._make_card()
        self.gen_lang_lbl = self._make_field_label()
        cl.addWidget(self.gen_lang_lbl)

        self.gen_lang_combo = QComboBox()
        self.gen_lang_combo.setMinimumHeight(42)
        self.gen_lang_combo.currentIndexChanged.connect(self._on_language_changed)
        cl.addWidget(self.gen_lang_combo)
        layout.addWidget(card)

        # Theme
        card, cl = self._make_card()
        self.gen_theme_lbl = self._make_field_label()
        cl.addWidget(self.gen_theme_lbl)

        self.gen_theme_combo = QComboBox()
        self.gen_theme_combo.setMinimumHeight(42)
        self.gen_theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        cl.addWidget(self.gen_theme_combo)
        layout.addWidget(card)

        # Date format
        card, cl = self._make_card()
        self.gen_date_lbl = self._make_field_label()
        cl.addWidget(self.gen_date_lbl)

        self.gen_date_combo = QComboBox()
        self.gen_date_combo.setMinimumHeight(42)
        self.gen_date_combo.addItem("YYYY-MM-DD", "YYYY-MM-DD")
        self.gen_date_combo.addItem("DD/MM/YYYY", "DD/MM/YYYY")
        self.gen_date_combo.addItem("MM/DD/YYYY", "MM/DD/YYYY")
        cl.addWidget(self.gen_date_combo)
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # --------------------------------------------------------
    # 2) Company
    # --------------------------------------------------------
    def _build_company(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        w.setObjectName("SectionPane")
        scroll.setWidget(w)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Logo card
        card, cl = self._make_card()
        self.com_logo_lbl = self._make_field_label()
        cl.addWidget(self.com_logo_lbl)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(16)

        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(120, 120)
        self.logo_preview.setObjectName("LogoPreview")
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setText("—")
        logo_row.addWidget(self.logo_preview)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)

        self.upload_logo_btn = QPushButton()
        self.upload_logo_btn.setObjectName("SecondaryBtn")
        self.upload_logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_logo_btn.setMinimumHeight(38)
        self.upload_logo_btn.clicked.connect(self._on_upload_logo)
        btn_col.addWidget(self.upload_logo_btn)

        self.remove_logo_btn = QPushButton()
        self.remove_logo_btn.setObjectName("DangerBtn")
        self.remove_logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_logo_btn.setMinimumHeight(38)
        self.remove_logo_btn.clicked.connect(self._on_remove_logo)
        btn_col.addWidget(self.remove_logo_btn)

        self.logo_hint = QLabel()
        self.logo_hint.setObjectName("Hint")
        btn_col.addWidget(self.logo_hint)

        btn_col.addStretch()
        logo_row.addLayout(btn_col, 1)
        cl.addLayout(logo_row)
        layout.addWidget(card)

        # Company info
        card, cl = self._make_card()

        self.com_name_lbl = self._make_field_label()
        cl.addWidget(self.com_name_lbl)
        self.com_name_input = QLineEdit()
        self.com_name_input.setMinimumHeight(42)
        cl.addWidget(self.com_name_input)

        self.com_addr_lbl = self._make_field_label()
        cl.addWidget(self.com_addr_lbl)
        self.com_addr_input = QLineEdit()
        self.com_addr_input.setMinimumHeight(42)
        cl.addWidget(self.com_addr_input)

        row = QHBoxLayout(); row.setSpacing(10)

        col1 = QVBoxLayout(); col1.setSpacing(4)
        self.com_phone_lbl = self._make_field_label()
        col1.addWidget(self.com_phone_lbl)
        self.com_phone_input = QLineEdit()
        self.com_phone_input.setMinimumHeight(42)
        col1.addWidget(self.com_phone_input)
        row.addLayout(col1, 1)

        col2 = QVBoxLayout(); col2.setSpacing(4)
        self.com_email_lbl = self._make_field_label()
        col2.addWidget(self.com_email_lbl)
        self.com_email_input = QLineEdit()
        self.com_email_input.setMinimumHeight(42)
        col2.addWidget(self.com_email_input)
        row.addLayout(col2, 1)

        cl.addLayout(row)

        self.com_website_lbl = self._make_field_label()
        cl.addWidget(self.com_website_lbl)
        self.com_website_input = QLineEdit()
        self.com_website_input.setMinimumHeight(42)
        cl.addWidget(self.com_website_input)

        layout.addWidget(card)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.com_save_btn = QPushButton()
        self.com_save_btn.setObjectName("PrimaryBtn")
        self.com_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.com_save_btn.setMinimumHeight(44)
        self.com_save_btn.setMinimumWidth(160)
        self.com_save_btn.clicked.connect(self._on_save_company)
        save_row.addWidget(self.com_save_btn)
        layout.addLayout(save_row)

        layout.addStretch()
        return scroll

    # --------------------------------------------------------
    # 3) Security
    # --------------------------------------------------------
    def _build_security(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        w.setObjectName("SectionPane")
        scroll.setWidget(w)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Change password
        card, cl = self._make_card()
        self.sec_change_lbl = QLabel()
        self.sec_change_lbl.setObjectName("CardTitle")
        cl.addWidget(self.sec_change_lbl)

        self.cur_pwd_lbl = self._make_field_label()
        cl.addWidget(self.cur_pwd_lbl)
        self.cur_pwd_input = QLineEdit()
        self.cur_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.cur_pwd_input.setMinimumHeight(42)
        cl.addWidget(self.cur_pwd_input)

        self.new_pwd_lbl = self._make_field_label()
        cl.addWidget(self.new_pwd_lbl)
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd_input.setMinimumHeight(42)
        cl.addWidget(self.new_pwd_input)

        self.conf_pwd_lbl = self._make_field_label()
        cl.addWidget(self.conf_pwd_lbl)
        self.conf_pwd_input = QLineEdit()
        self.conf_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf_pwd_input.setMinimumHeight(42)
        cl.addWidget(self.conf_pwd_input)

        pwd_btn_row = QHBoxLayout()
        pwd_btn_row.addStretch()
        self.update_pwd_btn = QPushButton()
        self.update_pwd_btn.setObjectName("PrimaryBtn")
        self.update_pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_pwd_btn.setMinimumHeight(42)
        self.update_pwd_btn.setMinimumWidth(180)
        self.update_pwd_btn.clicked.connect(self._on_change_password)
        pwd_btn_row.addWidget(self.update_pwd_btn)
        cl.addLayout(pwd_btn_row)
        layout.addWidget(card)

        # Auto-lock
        card, cl = self._make_card()
        self.sec_auto_lbl = QLabel()
        self.sec_auto_lbl.setObjectName("CardTitle")
        cl.addWidget(self.sec_auto_lbl)

        lock_row = QHBoxLayout()
        self.auto_lock_lbl = self._make_field_label()
        lock_row.addWidget(self.auto_lock_lbl)

        self.auto_lock_combo = QComboBox()
        self.auto_lock_combo.setMinimumHeight(42)
        self.auto_lock_combo.setMinimumWidth(150)
        self.auto_lock_combo.currentIndexChanged.connect(self._on_auto_lock_changed)
        lock_row.addWidget(self.auto_lock_combo)
        lock_row.addStretch()
        cl.addLayout(lock_row)
        layout.addWidget(card)

        layout.addStretch()
        return scroll

    # --------------------------------------------------------
    # 4) Backup
    # --------------------------------------------------------
    def _build_backup(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        w.setObjectName("SectionPane")
        scroll.setWidget(w)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Backup folder
        card, cl = self._make_card()
        self.data_folder_lbl = self._make_field_label()
        cl.addWidget(self.data_folder_lbl)
        data_row = QHBoxLayout()
        self.data_folder_input = QLineEdit(str(get_default_data_dir()))
        self.data_folder_input.setReadOnly(True)
        self.data_folder_input.setMinimumHeight(42)
        data_row.addWidget(self.data_folder_input, 1)
        self.change_data_folder_btn = QPushButton()
        self.change_data_folder_btn.setObjectName("SecondaryBtn")
        self.change_data_folder_btn.clicked.connect(self._on_change_data_folder)
        data_row.addWidget(self.change_data_folder_btn)
        cl.addLayout(data_row)

        self.bk_folder_lbl = self._make_field_label()
        cl.addWidget(self.bk_folder_lbl)

        folder_row = QHBoxLayout()
        self.bk_folder_input = QLineEdit()
        self.bk_folder_input.setText(str(get_backups_dir()))
        self.bk_folder_input.setReadOnly(True)
        self.bk_folder_input.setMinimumHeight(42)
        folder_row.addWidget(self.bk_folder_input, 1)

        self.change_backup_folder_btn = QPushButton()
        self.change_backup_folder_btn.setObjectName("SecondaryBtn")
        self.change_backup_folder_btn.clicked.connect(self._on_change_backup_folder)
        folder_row.addWidget(self.change_backup_folder_btn)

        self.open_folder_btn = QPushButton()
        self.open_folder_btn.setObjectName("SecondaryBtn")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.setMinimumHeight(42)
        self.open_folder_btn.clicked.connect(self._on_open_backup_folder)
        folder_row.addWidget(self.open_folder_btn)
        cl.addLayout(folder_row)

        options = QGridLayout()
        self.backup_interval_lbl = self._make_field_label()
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(5, 1440)
        self.backup_interval_spin.setValue(settings.get_int("auto_backup_minutes", 30))
        self.backup_interval_spin.valueChanged.connect(
            lambda value: settings.set("auto_backup_minutes", value)
        )
        self.backup_keep_lbl = self._make_field_label()
        self.backup_keep_spin = QSpinBox()
        self.backup_keep_spin.setRange(1, 200)
        self.backup_keep_spin.setValue(settings.get_int("backup_keep_count", 30))
        self.backup_keep_spin.valueChanged.connect(
            lambda value: settings.set("backup_keep_count", value)
        )
        options.addWidget(self.backup_interval_lbl, 0, 0)
        options.addWidget(self.backup_interval_spin, 0, 1)
        options.addWidget(self.backup_keep_lbl, 1, 0)
        options.addWidget(self.backup_keep_spin, 1, 1)
        cl.addLayout(options)

        # Create backup now
        create_row = QHBoxLayout()
        create_row.addStretch()
        self.create_backup_btn = QPushButton()
        self.create_backup_btn.setObjectName("PrimaryBtn")
        self.create_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_backup_btn.setMinimumHeight(44)
        self.create_backup_btn.setMinimumWidth(220)
        self.create_backup_btn.clicked.connect(self._on_create_backup)
        create_row.addWidget(self.create_backup_btn)
        cl.addLayout(create_row)
        layout.addWidget(card)

        # History
        card, cl = self._make_card()
        self.bk_hist_lbl = QLabel()
        self.bk_hist_lbl.setObjectName("CardTitle")
        cl.addWidget(self.bk_hist_lbl)

        self.backup_list_container = QVBoxLayout()
        self.backup_list_container.setSpacing(6)
        cl.addLayout(self.backup_list_container)

        layout.addWidget(card)
        layout.addStretch()
        return scroll

    def _refresh_backup_list(self):
        # امسح القائمة القديمة
        while self.backup_list_container.count():
            item = self.backup_list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        backups_dir = get_backups_dir()
        backups_dir.mkdir(parents=True, exist_ok=True)
        prefixes = ("backup_", "auto_", "before-restore_", "before-move_", "unfinished-local-")
        files = sorted(
            (path for path in backups_dir.rglob("*.zip") if path.name.startswith(prefixes)),
            key=lambda path: path.stat().st_mtime, reverse=True,
        )

        if not files:
            lbl = QLabel(_t("no_backups", self.language))
            lbl.setObjectName("Muted")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.backup_list_container.addWidget(lbl)
            return

        for f in files[:10]:
            row = QFrame()
            row.setObjectName("BackupRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(10)

            try:
                dt_str = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                size_str = _fmt_size(f.stat().st_size)
            except Exception:
                dt_str = f.stem
                size_str = "—"

            lbl = QLabel(f"{dt_str}  •  {size_str}")
            set_widget_stylesheet(lbl, "color: #FFFFFF; font-size: 13px;")
            rl.addWidget(lbl, 1)

            restore_btn = QPushButton(_t("restore", self.language))
            restore_btn.setObjectName("SmallBtn")
            restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_btn.setMinimumHeight(32)
            restore_btn.clicked.connect(lambda _, p=f: self._on_restore_backup(p))
            rl.addWidget(restore_btn)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("SmallDangerBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setFixedSize(32, 32)
            del_btn.clicked.connect(lambda _, p=f: self._on_delete_backup(p))
            rl.addWidget(del_btn)

            self.backup_list_container.addWidget(row)

    # --------------------------------------------------------
    # 5) Invoice
    # --------------------------------------------------------
    def _build_invoice(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        w.setObjectName("SectionPane")
        scroll.setWidget(w)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        card, cl = self._make_card()

        self.inv_prefix_lbl = self._make_field_label()
        cl.addWidget(self.inv_prefix_lbl)
        self.inv_prefix_input = QLineEdit()
        self.inv_prefix_input.setMinimumHeight(42)
        self.inv_prefix_input.editingFinished.connect(self._on_prefix_changed)
        cl.addWidget(self.inv_prefix_input)

        self.inv_next_lbl = self._make_field_label()
        cl.addWidget(self.inv_next_lbl)
        self.inv_next_input = QLineEdit()
        self.inv_next_input.setReadOnly(True)
        self.inv_next_input.setMinimumHeight(42)
        self.inv_next_input.setObjectName("ReadOnlyInput")
        cl.addWidget(self.inv_next_input)

        layout.addWidget(card)
        notes_card, notes_layout = self._make_card()
        self.invoice_notes_label = self._make_field_label()
        self.invoice_notes_input = _NotesCardEditor()
        self.invoice_notes2_label = self._make_field_label()
        self.invoice_notes2_input = _NotesCardEditor()
        for label, editor, key in ((self.invoice_notes_label, self.invoice_notes_input, "invoice_notes"), (self.invoice_notes2_label, self.invoice_notes2_input, "invoice_notes2")):
            notes_layout.addWidget(label)
            editor.setMinimumHeight(70)
            editor.setPlainText(settings.get(key) or "")
            notes_layout.addWidget(editor)
        self.save_invoice_notes_button = QPushButton()
        self.save_invoice_notes_button.clicked.connect(self._save_invoice_notes)
        notes_layout.addWidget(self.save_invoice_notes_button)
        layout.addWidget(notes_card)
        self._build_marks_controls(layout)
        layout.addStretch()
        return scroll

    def _build_images(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        pane = QWidget()
        pane.setObjectName("SectionPane")
        scroll.setWidget(pane)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        image_card, image_layout = self._make_card("صور layout" if self.language == "ar" else "layout images")
        self.layout_library_title = image_layout.itemAt(0).widget()
        self.layout_images_table = QTableWidget(0, 3)
        self.layout_images_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.layout_images_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.layout_images_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout_images_table.setIconSize(QSize(64, 40))
        self.layout_images_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        image_layout.addWidget(self.layout_images_table)
        self.layout_image_name = QLineEdit()
        self.layout_image_name.setPlaceholderText("اسم الصورة (اختياري؛ يُستخدم اسم الملف)" if self.language == "ar" else "Image name (optional; uses file name)")
        image_layout.addWidget(self.layout_image_name)
        buttons = QHBoxLayout()
        upload = QPushButton("رفع صورة" if self.language == "ar" else "Upload image")
        upload.clicked.connect(self._upload_layout_image)
        remove = QPushButton("حذف الصورة المحددة" if self.language == "ar" else "Delete selected image")
        remove.clicked.connect(self._delete_layout_image)
        refresh = QPushButton("تحديث" if self.language == "ar" else "Refresh")
        refresh.clicked.connect(self._refresh_layout_images)
        self.layout_upload_button = upload
        self.layout_delete_button = remove
        self.layout_refresh_button = refresh
        for button in (upload, remove, refresh):
            buttons.addWidget(button)
        image_layout.addLayout(buttons)
        layout.addWidget(image_card)
        self._refresh_layout_images()
        layout.addStretch()
        return scroll

    # --------------------------------------------------------
    # 6) About
    # --------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._resize_developer_logo)

    def _resize_developer_logo(self):
        if hasattr(self, "_about_logo") and not self._about_logo.isNull():
            self.about_developer_logo.setPixmap(self._about_logo.scaled(max(200, self.about_developer_logo.width() - 12), 230, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _build_marks_controls(self, layout):
        self.mark_controls = {}
        for kind, default_width, default_x in (("stamp", 30, 130), ("signature", 40, 140)):
            card, body = self._make_card()
            title = self._make_field_label()
            body.addWidget(title)
            filename = QLineEdit(settings.get("invoice_" + kind + "_label") or ("PNG / JPG" if settings.get("invoice_" + kind + "_image") else ""))
            filename.setReadOnly(True)
            body.addWidget(filename)
            buttons = QHBoxLayout()
            upload = QPushButton()
            upload.clicked.connect(lambda checked=False, k=kind: self._upload_mark(k))
            remove = QPushButton()
            remove.clicked.connect(lambda checked=False, k=kind: self._remove_mark(k))
            buttons.addWidget(upload); buttons.addWidget(remove); body.addLayout(buttons)
            form = QFormLayout()
            controls = dict(title=title, filename=filename, upload=upload, remove=remove)
            for field, default in (("width_mm", default_width), ("x_mm", default_x), ("y_mm", 5)):
                label = QLabel()
                spin = QDoubleSpinBox()
                spin.setDecimals(1)
                spin.setRange(1 if field == "width_mm" else 0, 277)
                spin.setSuffix(" mm")
                try:spin.setValue(float(settings.get("invoice_" + kind + "_" + field, default)))
                except (TypeError, ValueError):spin.setValue(default)
                spin.valueChanged.connect(lambda value, k=kind, f=field: settings.set("invoice_" + k + "_" + f, value))
                form.addRow(label, spin); controls[field] = spin; controls[field + "_label"] = label
            body.addLayout(form);layout.addWidget(card);self.mark_controls[kind] = controls

    def _upload_mark(self, kind):
        source, _ = QFileDialog.getOpenFileName(self, "PNG / JPG", "", "Images (*.png *.jpg *.jpeg)")
        if not source:return
        try:
            from PIL import Image
            import uuid
            path = Path(source)
            if path.stat().st_size > 5 * 1024 * 1024:raise ValueError("حجم الصورة أكبر من 5 MB / Image exceeds 5 MB")
            with Image.open(path) as image:image.verify()
            directory = get_images_dir() / "Marks"
            directory.mkdir(parents=True, exist_ok=True)
            filename = kind + "-" + uuid.uuid4().hex + path.suffix.lower()
            shutil.copy2(path, directory / filename)
            settings.set("invoice_" + kind + "_image", filename)
            settings.set("invoice_" + kind + "_label", path.name)
            self.mark_controls[kind]["filename"].setText(path.name)
        except Exception as error:QMessageBox.warning(self, _t("err_title", self.language), str(error))

    def _remove_mark(self, kind):
        settings.set("invoice_" + kind + "_image", "")
        settings.set("invoice_" + kind + "_label", "")
        self.mark_controls[kind]["filename"].clear()

    def _save_invoice_notes(self):
        settings.set("invoice_notes", self.invoice_notes_input.toPlainText())
        settings.set("invoice_notes2", self.invoice_notes2_input.toPlainText())
        QMessageBox.information(self, _t("info_title", self.language), _t("saved", self.language))

    def _refresh_layout_images(self):
        self.layout_images_table.setHorizontalHeaderLabels(["الاسم" if self.language == "ar" else "Name", "layout", "الأصناف المرتبطة" if self.language == "ar" else "Products using image"])
        images = product_service.get_layout_images()
        self.layout_images_table.setRowCount(len(images))
        for index, image in enumerate(images):
            name = QTableWidgetItem(image["name"])
            name.setData(Qt.ItemDataRole.UserRole, image["filename"])
            self.layout_images_table.setItem(index, 0, name)
            preview = QTableWidgetItem()
            path = product_service.get_image_path(image["filename"])
            if path:
                preview.setIcon(QIcon(str(path)))
            self.layout_images_table.setItem(index, 1, preview)
            self.layout_images_table.setItem(index, 2, QTableWidgetItem(str(image["uses"])))
            self.layout_images_table.setRowHeight(index, 50)
        self.layout_images_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.layout_images_table.setFixedHeight(self.layout_images_table.horizontalHeader().height() + 50 * max(1, len(images)) + 4)


    def _upload_layout_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "layout", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            product_service.add_layout_image(self.layout_image_name.text(), path)
            self.layout_image_name.clear()
            self._refresh_layout_images()
        except (ProductError, OSError) as error:
            QMessageBox.warning(self, "layout", str(error))

    def _delete_layout_image(self):
        row = self.layout_images_table.currentRow()
        if row < 0:
            return
        filename = self.layout_images_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "layout", "حذف الصورة المحددة؟" if self.language == "ar" else "Delete the selected image?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            product_service.delete_layout_image(filename)
            self._refresh_layout_images()
        except (ProductError, OSError) as error:
            QMessageBox.warning(self, "layout", str(error))

    def _build_about(self):
        w = QWidget()
        w.setObjectName("SectionPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        card, cl = self._make_card()
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.setSpacing(12)

        card._fixed_theme = "dark"
        card.setObjectName("AboutDeveloperCard")
        set_widget_stylesheet(card, "QFrame#AboutDeveloperCard {background: #0F1D35; border: 1px solid #25456A; border-radius: 12px;} QLabel {color: #FFFFFF; background: transparent;}")
        from app.ui.main_window import get_developer_logo_path, DEVELOPER_PERSON_AR, DEVELOPER_NAME_AR, DEVELOPER_PHONE, DEVELOPER_EMAIL
        self.about_developer_logo = QLabel()
        self.about_developer_logo.setMinimumHeight(190)
        self.about_developer_logo.setMaximumHeight(260)
        self.about_developer_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_developer_logo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        set_widget_stylesheet(self.about_developer_logo, "background: transparent; border: none;")
        self._about_logo = QPixmap(str(get_developer_logo_path()))
        cl.addWidget(self.about_developer_logo)
        for text in (DEVELOPER_PERSON_AR, DEVELOPER_NAME_AR, DEVELOPER_PHONE, DEVELOPER_EMAIL):
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("InfoValue")
            cl.addWidget(label)
        QTimer.singleShot(0, self._resize_developer_logo)

        app_lbl = QLabel(APP_NAME)
        app_lbl.setObjectName("AboutAppName")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(app_lbl)

        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("AboutVersion")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ver_lbl)

        author_lbl = QLabel(APP_AUTHOR)
        author_lbl.setObjectName("AboutAuthor")
        author_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(author_lbl)

        layout.addWidget(card)

        # System info
        card, cl = self._make_card()

        info_grid = QGridLayout()
        info_grid.setSpacing(10)

        self.about_data_lbl = self._make_field_label()
        info_grid.addWidget(self.about_data_lbl, 0, 0)
        self.about_data_value = QLabel(str(get_default_data_dir()))
        self.about_data_value.setWordWrap(True)
        self.about_data_value.setObjectName("InfoValue")
        info_grid.addWidget(self.about_data_value, 0, 1)

        self.about_db_lbl = self._make_field_label()
        info_grid.addWidget(self.about_db_lbl, 1, 0)
        self.about_db_value = QLabel("")
        self.about_db_value.setObjectName("InfoValue")
        info_grid.addWidget(self.about_db_value, 1, 1)

        cl.addLayout(info_grid)
        layout.addWidget(card)

        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(w)
        return scroll

    # --------------------------------------------------------
    # 7) Danger Zone
    # --------------------------------------------------------
    def _build_danger(self):
        w = QWidget()
        w.setObjectName("SectionPane")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        warn = QLabel()
        warn.setObjectName("DangerWarning")
        warn.setWordWrap(True)
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.danger_warning_lbl = warn
        layout.addWidget(warn)

        card = QFrame()
        card.setObjectName("DangerCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(12)

        self.reset_title_lbl = QLabel()
        self.reset_title_lbl.setObjectName("CardTitle")
        cl.addWidget(self.reset_title_lbl)

        self.reset_desc_lbl = QLabel()
        self.reset_desc_lbl.setObjectName("Muted")
        self.reset_desc_lbl.setWordWrap(True)
        cl.addWidget(self.reset_desc_lbl)

        reset_btn_row = QHBoxLayout()
        reset_btn_row.addStretch()
        self.reset_btn = QPushButton()
        self.reset_btn.setObjectName("DangerBtn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setMinimumHeight(44)
        self.reset_btn.setMinimumWidth(220)
        self.reset_btn.clicked.connect(self._on_reset_app)
        reset_btn_row.addWidget(self.reset_btn)
        cl.addLayout(reset_btn_row)

        layout.addWidget(card)
        layout.addStretch()
        return w

    # --------------------------------------------------------
    # Switch section
    # --------------------------------------------------------
    def _switch_section(self, key):
        self.current_section = key
        indices = {
            "general": 0, "company": 1, "security": 2,
            "backup": 3, "invoice": 4, "images": 5, "about": 6, "danger": 7,
        }
        self.stack.setCurrentIndex(indices.get(key, 0))

        for k, btn in self.sidebar_buttons.items():
            active = (k == key)
            btn.setProperty("active", active)
            btn.setChecked(active)
            btn.style().unpolish(btn); btn.style().polish(btn)

        if key == "backup":
            self._refresh_backup_list()
        elif key == "about":
            self._refresh_about_info()
            QTimer.singleShot(0, self._resize_developer_logo)
        elif key == "images":
            self._refresh_layout_images()

    # --------------------------------------------------------
    # النصوص
    # --------------------------------------------------------
    def _reload_texts(self):
        lang = self.language
        self.title.setText(_t("title", lang))
        self.subtitle.setText(_t("subtitle", lang))

        for key, btn in self.sidebar_buttons.items():
            btn.setText(_t(btn.property("text_key"), lang))

        # General
        self.gen_lang_lbl.setText(_t("language", lang))
        self.gen_theme_lbl.setText(_t("theme", lang))
        self.gen_date_lbl.setText(_t("date_format", lang))

        cur_lang = self.gen_lang_combo.currentData() if self.gen_lang_combo.count() else settings.get("language", "en")
        self.gen_lang_combo.blockSignals(True)
        self.gen_lang_combo.clear()
        self.gen_lang_combo.addItem(_t("english", lang), "en")
        self.gen_lang_combo.addItem(_t("arabic", lang), "ar")
        for i in range(self.gen_lang_combo.count()):
            if self.gen_lang_combo.itemData(i) == cur_lang:
                self.gen_lang_combo.setCurrentIndex(i); break
        self.gen_lang_combo.blockSignals(False)

        cur_theme = self.gen_theme_combo.currentData() if self.gen_theme_combo.count() else settings.get("theme", "dark")
        self.gen_theme_combo.blockSignals(True)
        self.gen_theme_combo.clear()
        self.gen_theme_combo.addItem(_t("dark", lang), "dark")
        self.gen_theme_combo.addItem(_t("light", lang), "light")
        for i in range(self.gen_theme_combo.count()):
            if self.gen_theme_combo.itemData(i) == cur_theme:
                self.gen_theme_combo.setCurrentIndex(i); break
        self.gen_theme_combo.blockSignals(False)

        cur_date_fmt = settings.get("date_format", "YYYY-MM-DD")
        for i in range(self.gen_date_combo.count()):
            if self.gen_date_combo.itemData(i) == cur_date_fmt:
                self.gen_date_combo.setCurrentIndex(i); break

        # Company
        self.com_logo_lbl.setText(_t("company_logo", lang))
        self.upload_logo_btn.setText(_t("upload_logo", lang))
        self.remove_logo_btn.setText(_t("remove_logo", lang))
        self.logo_hint.setText(_t("logo_hint", lang))
        self.com_name_lbl.setText(_t("company_name", lang))
        self.com_addr_lbl.setText(_t("company_address", lang))
        self.com_phone_lbl.setText(_t("company_phone", lang))
        self.com_email_lbl.setText(_t("company_email", lang))
        self.com_website_lbl.setText(_t("company_website", lang))
        self.com_save_btn.setText(_t("btn_save", lang))

        # Security
        self.sec_change_lbl.setText(_t("change_password", lang))
        self.cur_pwd_lbl.setText(_t("current_password", lang))
        self.new_pwd_lbl.setText(_t("new_password", lang))
        self.conf_pwd_lbl.setText(_t("confirm_password", lang))
        self.update_pwd_btn.setText(_t("update_password", lang))
        self.sec_auto_lbl.setText(_t("auto_lock", lang))
        self.auto_lock_lbl.setText(_t("auto_lock_after", lang))

        cur_lock = settings.get_int("auto_lock_minutes", 10)
        self.auto_lock_combo.blockSignals(True)
        self.auto_lock_combo.clear()
        for n in [5, 10, 15, 30, 60]:
            self.auto_lock_combo.addItem(f"{n} {_t('minutes', lang)}", n)
        self.auto_lock_combo.addItem(_t("never", lang), 0)
        for i in range(self.auto_lock_combo.count()):
            if self.auto_lock_combo.itemData(i) == cur_lock:
                self.auto_lock_combo.setCurrentIndex(i); break
        self.auto_lock_combo.blockSignals(False)

        # Backup
        self.bk_folder_lbl.setText(_t("backup_location", lang))
        self.data_folder_lbl.setText(_t("data_folder", lang))
        self.change_data_folder_btn.setText(_t("change_folder", lang))
        self.change_backup_folder_btn.setText(_t("change_folder", lang))
        self.backup_interval_lbl.setText(_t("backup_interval", lang))
        self.backup_keep_lbl.setText(_t("backup_keep", lang))
        self.open_folder_btn.setText(_t("open_folder", lang))
        self.create_backup_btn.setText(_t("create_backup", lang))
        self.bk_hist_lbl.setText(_t("backup_history", lang))

        # Invoice
        for kind, controls in self.mark_controls.items():
            controls["title"].setText(("الختم" if kind == "stamp" else "التوقيع") if lang == "ar" else kind.title())
            controls["upload"].setText("رفع صورة" if lang == "ar" else "Upload image")
            controls["remove"].setText("إزالة" if lang == "ar" else "Remove")
            for field, ar, en in (("width_mm", "العرض", "Width"), ("x_mm", "المسافة من اليسار", "Distance from left"), ("y_mm", "المسافة تحت الملاحظات", "Distance below notes")):
                controls[field + "_label"].setText(ar if lang == "ar" else en)
        self.invoice_notes_label.setText("الملاحظات" if lang == "ar" else "Notes")
        self.invoice_notes2_label.setText("ملاحظات 2" if lang == "ar" else "Notes 2")
        self.save_invoice_notes_button.setText("حفظ الملاحظات" if lang == "ar" else "Save notes")
        self.layout_library_title.setText("صور layout" if lang == "ar" else "layout images")
        self.layout_image_name.setPlaceholderText("اسم الصورة (اختياري؛ يُستخدم اسم الملف)" if lang == "ar" else "Image name (optional; uses file name)")
        self.layout_upload_button.setText("رفع صورة" if lang == "ar" else "Upload image")
        self.layout_delete_button.setText("حذف الصورة المحددة" if lang == "ar" else "Delete selected image")
        self.layout_refresh_button.setText("تحديث" if lang == "ar" else "Refresh")
        self._refresh_layout_images()
        self.inv_prefix_lbl.setText(_t("default_prefix", lang))
        self.inv_next_lbl.setText(_t("next_invoice_no", lang))

        # About
        self.about_data_lbl.setText(_t("data_location", lang))
        self.about_db_lbl.setText(_t("db_size", lang))

        # Danger
        self.danger_warning_lbl.setText(_t("danger_warning", lang))
        self.reset_title_lbl.setText(_t("reset_app", lang))
        self.reset_desc_lbl.setText(_t("reset_desc", lang))
        self.reset_btn.setText(_t("reset_app", lang))

        # Update UI from settings
        self._load_company_data()
        self._load_logo_preview()
        self._load_invoice_data()

    # --------------------------------------------------------
    # Load / Save
    # --------------------------------------------------------
    def _load_company_data(self):
        self.com_name_input.setText(settings.get("company_name") or "")
        self.com_addr_input.setText(settings.get("company_address") or "")
        self.com_phone_input.setText(settings.get("company_phone") or "")
        self.com_email_input.setText(settings.get("company_email") or "")
        self.com_website_input.setText(settings.get("company_website") or "")

    def _load_logo_preview(self):
        filename = settings.get("company_logo") or ""
        if filename:
            path = get_company_dir() / filename
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    self.logo_preview.setPixmap(
                        pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
                    )
                    self.logo_preview.setText("")
                    return
        self.logo_preview.clear()
        self.logo_preview.setText("—")

    def _load_invoice_data(self):
        prefix = settings.get("invoice_prefix") or "INV-"
        self.inv_prefix_input.setText(prefix)
        from app.services.invoice_service import invoice_service
        self.inv_next_input.setText(invoice_service.generate_invoice_number())

    def _refresh_about_info(self):
        try:
            db_path = get_db_path()
            if db_path.exists():
                self.about_db_value.setText(_fmt_size(db_path.stat().st_size))
            else:
                self.about_db_value.setText("—")
        except Exception:
            self.about_db_value.setText("—")

    # --------------------------------------------------------
    # Events
    # --------------------------------------------------------
    def _on_language_changed(self):
        new_lang = self.gen_lang_combo.currentData()
        if new_lang and new_lang != self.language:
            settings.set("language", new_lang)
            self.language = new_lang
            self.language_changed.emit(new_lang)

    def _on_theme_changed(self):
        new_theme = self.gen_theme_combo.currentData()
        if new_theme and new_theme != self.theme:
            settings.set("theme", new_theme)
            self.theme = new_theme
            self.theme_changed.emit(new_theme)

    def _on_save_company(self):
        settings.set("company_name", self.com_name_input.text().strip())
        settings.set("company_address", self.com_addr_input.text().strip())
        settings.set("company_phone", self.com_phone_input.text().strip())
        settings.set("company_email", self.com_email_input.text().strip())
        settings.set("company_website", self.com_website_input.text().strip())
        QMessageBox.information(
            self, _t("info_title", self.language),
            _t("saved", self.language),
        )

    def _on_upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _t("upload_logo", self.language), "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if not path:
            return

        src = Path(path)
        if src.stat().st_size > 2 * 1024 * 1024:
            QMessageBox.warning(self, _t("err_title", self.language),
                                "Image too large (max 2 MB)")
            return

        # انسخ إلى مجلد الشركة
        company_dir = get_company_dir()
        company_dir.mkdir(parents=True, exist_ok=True)

        ext = src.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            QMessageBox.warning(self, _t("err_title", self.language),
                                "Only PNG/JPG allowed")
            return

        # احذف الشعار القديم
        old = settings.get("company_logo") or ""
        if old:
            old_path = company_dir / old
            try:
                if old_path.exists():
                    old_path.unlink()
            except OSError:
                pass

        target_name = f"logo{ext}"
        target = company_dir / target_name
        try:
            shutil.copy2(src, target)
            settings.set("company_logo", target_name)
            self._load_logo_preview()
            QMessageBox.information(
                self, _t("info_title", self.language),
                _t("saved", self.language),
            )
        except Exception as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_remove_logo(self):
        old = settings.get("company_logo") or ""
        if not old:
            return
        reply = QMessageBox.question(
            self, _t("confirm_title", self.language),
            _t("remove_logo", self.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            old_path = get_company_dir() / old
            if old_path.exists():
                old_path.unlink()
        except OSError:
            pass
        settings.set("company_logo", "")
        self._load_logo_preview()

    def _on_change_password(self):
        try:
            auth.change_password(
                self.cur_pwd_input.text(),
                self.new_pwd_input.text(),
                self.conf_pwd_input.text(),
            )
            self.cur_pwd_input.clear()
            self.new_pwd_input.clear()
            self.conf_pwd_input.clear()
            QMessageBox.information(
                self, _t("info_title", self.language),
                _t("saved", self.language),
            )
        except AuthError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_auto_lock_changed(self):
        val = self.auto_lock_combo.currentData()
        if val is not None:
            settings.set("auto_lock_minutes", val)

    def _on_prefix_changed(self):
        prefix = self.inv_prefix_input.text().strip() or "INV-"
        settings.set("invoice_prefix", prefix)
        self.inv_prefix_input.setText(prefix)
        self._load_invoice_data()

    def _on_open_backup_folder(self):
        path = get_backups_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(path))
        except Exception:
            pass

    def _on_change_backup_folder(self):
        selected = QFileDialog.getExistingDirectory(
            self, _t("backup_location", self.language), str(get_backups_dir())
        )
        if not selected:
            return
        try:
            validate_backup_dir(Path(selected))
            update_storage_config(backup_dir=selected)
        except Exception as exc:
            QMessageBox.warning(self, _t("err_title", self.language), str(exc))
            return
        self.bk_folder_input.setText(selected)
        QMessageBox.information(
            self, _t("info_title", self.language), _t("restart_storage", self.language)
        )
        QApplication.exit(RESTART_EXIT_CODE)

    def _on_change_data_folder(self):
        selected = QFileDialog.getExistingDirectory(
            self, _t("data_folder", self.language), str(get_default_data_dir())
        )
        if not selected:
            return
        try:
            target = Path(selected).resolve()
            target.mkdir(parents=True, exist_ok=True)
            from app.paths import get_shared_db_path
            existing = target / "app.db"
            if existing.exists() and existing.resolve() != get_shared_db_path().resolve():
                answer = QMessageBox.question(
                    self, "بيانات موجودة", "هذا المجلد يحتوي قاعدة بيانات. هل تريد استخدامها بعد إعادة التشغيل؟ لن تُستبدل ببيانات الجهاز الحالية.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                update_storage_config(data_dir=str(target))
                QApplication.exit(RESTART_EXIT_CODE)
                return
            if existing.resolve() == get_shared_db_path().resolve():
                return
            backup_service.create_backup(
                prefix="before-move",
                keep=settings.get_int("backup_keep_count", 30),
            )
            from app.db import db
            db.backup_to(target / "app.db")
            source_images = get_images_dir()
            if source_images.exists():
                shutil.copytree(source_images, target / "Images", dirs_exist_ok=True)
            update_storage_config(data_dir=str(target))
            self.data_folder_input.setText(str(target))
            QMessageBox.information(
                self, _t("info_title", self.language), _t("restart_storage", self.language)
            )
            QApplication.exit(RESTART_EXIT_CODE)
        except Exception as exc:
            QMessageBox.warning(self, _t("err_title", self.language), str(exc))

    def _on_create_backup(self):
        try:
            backup_path = backup_service.create_backup(
                prefix="backup", keep=settings.get_int("backup_keep_count", 30)
            )

            self._refresh_backup_list()
            QMessageBox.information(
                self, _t("info_title", self.language),
                _t("backup_created", self.language, path=str(backup_path)),
            )
        except Exception as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_restore_backup(self, backup_path: Path):
        reply = QMessageBox.question(
            self, _t("confirm_title", self.language),
            _t("confirm_restore", self.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            backup_service.restore_backup(backup_path)

            QMessageBox.information(
                self, _t("info_title", self.language),
                _t("restore_done", self.language),
            )
            QApplication.exit(RESTART_EXIT_CODE)
        except Exception as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_delete_backup(self, backup_path: Path):
        reply = QMessageBox.question(
            self, _t("confirm_title", self.language),
            _t("confirm_delete_bk", self.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            backup_path.unlink()
            self._refresh_backup_list()
        except Exception as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_reset_app(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("reset_app", self.language))
        dlg.setModal(True)
        dlg.setMinimumWidth(420)
        set_widget_stylesheet(dlg, """
            QDialog { background-color: #0A1220; }
            QLabel { color: #FFFFFF; font-size: 14px; background: transparent; }
            QLineEdit {
                background-color: rgba(15, 29, 53, 0.9); color: #FFFFFF;
                border: 1px solid rgba(220,38,38,0.5); border-radius: 8px;
                padding: 8px 12px; font-size: 14px;
            }
            QPushButton {
                border-radius: 8px; padding: 8px 18px; font-weight: 600;
                font-size: 13px;
            }
            QPushButton#DangerBtn {
                background-color: #DC2626; color: #FFFFFF; border: none;
            }
            QPushButton#DangerBtn:hover { background-color: #EF4444; }
            QPushButton#SecondaryBtn {
                background-color: transparent; color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.15);
            }
        """)

        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(24, 24, 24, 24)
        vl.setSpacing(14)

        lbl = QLabel(_t("confirm_reset", self.language))
        lbl.setWordWrap(True)
        set_widget_stylesheet(lbl, "color: #F87171; font-weight: 600;")
        vl.addWidget(lbl)

        confirm_input = QLineEdit()
        confirm_input.setPlaceholderText("DELETE")
        vl.addWidget(confirm_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(_t("remove_logo", self.language) if False else "Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton(_t("reset_app", self.language))
        ok_btn.setObjectName("DangerBtn")
        ok_btn.setEnabled(False)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)

        confirm_input.textChanged.connect(
            lambda t: ok_btn.setEnabled(t.strip() == "DELETE")
        )
        vl.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from app.db import db
                db.reset(get_db_path())
                db.connect(get_db_path())
                settings.clear_cache()
                QMessageBox.information(
                    self, _t("info_title", self.language),
                    _t("reset_done", self.language),
                )
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            except Exception as e:
                QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def reload_language(self, language):
        self.language = language
        self._reload_texts()
        self._switch_section(self.current_section)

    # --------------------------------------------------------
    # الأنماط
    # --------------------------------------------------------
    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; color: #FFFFFF; }
            QWidget#SettingsContent { background-color: #000000; }
            QWidget#SectionPane { background-color: #000000; }
            QFrame#SettingsSidebar {
                background-color: rgba(15, 29, 53, 0.7);
                border-right: 1px solid rgba(37, 99, 235, 0.2);
            }
            QPushButton#SettingsNavBtn {
                background-color: transparent;
                color: rgba(203, 213, 225, 0.9);
                text-align: left;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#SettingsNavBtn:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #FFFFFF;
            }
            QPushButton#SettingsNavBtn[active="true"] {
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
            QFrame#Card {
                background-color: rgba(15, 29, 53, 0.7);
                border: 1px solid rgba(37, 99, 235, 0.2);
                border-radius: 12px;
            }
            QFrame#DangerCard {
                background-color: rgba(220, 38, 38, 0.08);
                border: 1px solid rgba(220, 38, 38, 0.4);
                border-radius: 12px;
            }
            QFrame#BackupRow {
                background-color: rgba(10, 22, 40, 0.6);
                border: 1px solid rgba(37, 99, 235, 0.15);
                border-radius: 8px;
            }
            QLabel#CardTitle {
                color: #FFFFFF; font-size: 15px; font-weight: 600;
                background: transparent;
            }
            QLabel#FieldLabel {
                color: rgba(148,163,184,0.9); font-size: 12px;
                background: transparent;
            }
            QLabel#Hint {
                color: rgba(148,163,184,0.6); font-size: 11px;
                background: transparent;
            }
            QLabel#Muted {
                color: rgba(148,163,184,0.85); font-size: 13px;
                background: transparent;
            }
            QLabel#InfoValue {
                color: #FFFFFF; font-size: 13px;
                background: transparent;
            }
            QLabel#LogoPreview {
                background-color: rgba(15, 29, 53, 0.7);
                border: 2px dashed rgba(37, 99, 235, 0.35);
                border-radius: 12px;
                color: rgba(148,163,184,0.6);
                font-size: 14px;
            }
            QLabel#DangerWarning {
                color: #F87171;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
                padding: 12px;
            }
            QLabel#AboutAppName {
                color: #FFFFFF; font-size: 20px; font-weight: 700;
                background: transparent;
            }
            QLabel#AboutVersion {
                color: #60A5FA; font-size: 14px; font-weight: 600;
                background: transparent;
            }
            QLabel#AboutAuthor {
                color: rgba(148,163,184,0.9); font-size: 13px;
                background: transparent;
            }
            QTextEdit#InvoiceNotesEditor {
                background-color: rgba(15, 29, 53, 0.9);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit, QComboBox {
                background-color: rgba(15, 29, 53, 0.9);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #2563EB;
            }
            QLineEdit#ReadOnlyInput {
                background-color: rgba(10, 22, 40, 0.9);
                color: #A0B8D8;
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: rgba(15, 29, 53, 0.98);
                color: #FFFFFF;
                selection-background-color: #2563EB;
                border: 1px solid rgba(37, 99, 235, 0.5);
                border-radius: 8px;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563EB; color: #FFFFFF;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
                padding: 10px 20px;
            }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn {
                background-color: rgba(15, 29, 53, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(37, 99, 235, 0.35);
                border-radius: 8px;
                font-size: 13px; font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: rgba(37, 99, 235, 0.2);
                border: 1px solid rgba(37, 99, 235, 0.6);
            }
            QPushButton#DangerBtn {
                background-color: rgba(220, 38, 38, 0.15);
                color: #F87171;
                border: 1px solid rgba(220, 38, 38, 0.5);
                border-radius: 8px;
                font-size: 13px; font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton#DangerBtn:hover {
                background-color: rgba(220, 38, 38, 0.35);
                color: #FFFFFF;
            }
            QPushButton#SmallBtn {
                background-color: rgba(37, 99, 235, 0.15);
                color: #60A5FA;
                border: 1px solid rgba(37, 99, 235, 0.4);
                border-radius: 6px;
                font-size: 12px; font-weight: 500;
                padding: 4px 12px;
            }
            QPushButton#SmallBtn:hover {
                background-color: rgba(37, 99, 235, 0.35);
                color: #FFFFFF;
            }
            QPushButton#SmallDangerBtn {
                background-color: rgba(220, 38, 38, 0.15);
                color: #F87171;
                border: 1px solid rgba(220, 38, 38, 0.4);
                border-radius: 6px;
                font-size: 13px;
                padding: 0;
            }
            QPushButton#SmallDangerBtn:hover {
                background-color: rgba(220, 38, 38, 0.4);
                color: #FFFFFF;
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
