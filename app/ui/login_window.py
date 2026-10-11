"""
شاشة تسجيل الدخول.
"""
import secrets
import time
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox, QMessageBox,
)

from app.config import (
    APP_NAME, APP_VERSION, APP_COPYRIGHT, PASSWORD_MIN_LENGTH,
    MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_SECONDS,
)
from app.services.auth_service import auth, AuthError
from app.services.settings_service import settings
from app.ui.theme import get_palette
from app.ui.theme import set_widget_stylesheet


class LoginWindow(QWidget):
    """
    نافذة الدخول.
    
    تُصدر إشارة login_successful عند نجاح الدخول.
    """
    login_successful = Signal()

    def __init__(self):
        super().__init__()
        self._fixed_theme = "dark"
        self.theme = self._fixed_theme
        self.palette_data = get_palette(self.theme)
        self._failed_attempts = 0
        self._lock_until = float(settings.get("login_lock_until", 0) or 0)
        self._setup_ui()
        self._apply_style()
        self._restore_lockout_state()
        from app.ui.main_window import enable_dark_title_bar
        enable_dark_title_bar(self)

    # --------------------------------------------------------
    # واجهة المستخدم
    # --------------------------------------------------------
    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} — Login")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "app_icon.ico")))
        self.setMinimumSize(640, 560)
        self.resize(1100, 720)
        self.setObjectName("LoginRoot")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)

        main_layout.addStretch()

        # ===== البطاقة =====
        self.card = QFrame()
        self.card.setObjectName("Card")
        self.card.setFixedWidth(420)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 24, 32, 30)
        card_layout.setSpacing(16)

        # --- الشعار ---
        self.logo_label = QLabel("A")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFixedSize(340, 130)
        self.logo_label.setObjectName("DeveloperLogo")
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
        if logo_path.is_file():
            logo = QPixmap(str(logo_path))
            if not logo.isNull():
                self.logo_label.setPixmap(logo.scaled(
                    320, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
                self.logo_label.setText("")
        logo_container = QHBoxLayout()
        logo_container.addStretch()
        logo_container.addWidget(self.logo_label)
        logo_container.addStretch()
        card_layout.addLayout(logo_container)

        # --- فاصل مزخرف ---
        divider = QLabel("──────  ●  ──────")
        divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        divider.setObjectName("Divider")
        card_layout.addWidget(divider)

        # --- اسم التطبيق ---
        self.app_title = QLabel(APP_NAME)
        self.app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.app_title.setObjectName("AppTitle")
        card_layout.addWidget(self.app_title)

        card_layout.addSpacing(10)

        # --- حقل كلمة المرور ---
        self.pass_label = QLabel("Password" if not self._is_arabic() else "كلمة المرور")
        self.pass_label.setObjectName("FieldLabel")
        card_layout.addWidget(self.pass_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("•" * 10)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_unlock)
        card_layout.addWidget(self.password_input)

        # --- تلميح كلمة المرور (يظهر عند الإنشاء) ---
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("Hint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setVisible(False)
        card_layout.addWidget(self.hint_label)

        # --- صف الخيارات ---
        options_row = QHBoxLayout()
        self.remember_cb = QCheckBox("Remember me")
        self.remember_cb.setVisible(False)  # لاحقًا
        options_row.addWidget(self.remember_cb)
        options_row.addStretch()

        self.forgot_btn = QPushButton("Forgot Password?")
        self.forgot_btn.setObjectName("LinkButton")
        self.forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forgot_btn.clicked.connect(self._on_forgot_password)
        options_row.addWidget(self.forgot_btn)

        card_layout.addLayout(options_row)

        # --- زر الفتح ---
        self.unlock_btn = QPushButton("🔓  Unlock")
        self.unlock_btn.setObjectName("Primary")
        self.unlock_btn.setMinimumHeight(46)
        self.unlock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unlock_btn.clicked.connect(self._on_unlock)
        card_layout.addWidget(self.unlock_btn)

        self.exit_btn = QPushButton("Exit" if not self._is_arabic() else "خروج")
        self.exit_btn.setObjectName("LinkButton")
        self.exit_btn.setMinimumHeight(40)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(QApplication.instance().quit)
        card_layout.addWidget(self.exit_btn)

        # --- رسالة الخطأ ---
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorMsg")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()

        # --- تذييل ---
        footer = QLabel(f"v{APP_VERSION}\n{APP_COPYRIGHT}")
        footer.setWordWrap(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("Footer")
        main_layout.addWidget(footer)

        # هل هذه أول مرة (لا توجد كلمة مرور)؟
        self._check_first_run()

    # --------------------------------------------------------
    # مساعدات
    # --------------------------------------------------------
    def _is_arabic(self) -> bool:
        return settings.get("language") == "ar"

    def _check_first_run(self):
        """إذا لم توجد كلمة مرور، نطلب إنشاءها."""
        if not auth.has_password():
            self.app_title.setText("Welcome" if not self._is_arabic() else "مرحبًا")
            self.pass_label.setText("Create a password" if not self._is_arabic() else "أنشئ كلمة مرور")
            self.unlock_btn.setText("Create & Continue" if not self._is_arabic() else "إنشاء ومتابعة")
            self.forgot_btn.setVisible(False)
            self.hint_label.setText(
                f"Minimum {PASSWORD_MIN_LENGTH} characters. "
                "You will need it every time you open the app."
                if not self._is_arabic() else
                f"الحد الأدنى {PASSWORD_MIN_LENGTH} أحرف. ستحتاجها في كل مرة تفتح البرنامج."
            )
            self.hint_label.setVisible(True)
            self.password_input.setPlaceholderText(
                "Enter new password" if not self._is_arabic() else "أدخل كلمة المرور الجديدة"
            )
        else:
            self.password_input.setPlaceholderText(
                "Enter your password" if not self._is_arabic() else "أدخل كلمة المرور"
            )

    # --------------------------------------------------------
    # الأحداث
    # --------------------------------------------------------
    def _on_unlock(self):
        now = time.time()
        remaining = auth.lockout_remaining(now)
        if remaining:
            self._show_error(
                f"Too many failed attempts. Try again in {remaining} seconds."
                if not self._is_arabic()
                else f"محاولات كثيرة خاطئة. حاول مرة أخرى بعد {remaining} ثانية."
            )
            return

        password = self.password_input.text().strip()

        if not password:
            self._show_error(
                "Please enter a password." if not self._is_arabic()
                else "الرجاء إدخال كلمة المرور."
            )
            return

        if not auth.has_password():
            try:
                auth.set_password(password)
                self._show_success_and_continue()
            except AuthError as e:
                self._show_error(str(e))
            return

        if auth.verify_password(password):
            self._failed_attempts = 0
            self._lock_until = 0.0
            auth.clear_login_failures()
            self.unlock_btn.setEnabled(True)
            self.password_input.setEnabled(True)
            self.login_successful.emit()
            return

        remaining, locked_for = auth.register_failed_login(now)
        self._failed_attempts = MAX_LOGIN_ATTEMPTS - remaining if remaining else 0

        if locked_for:
            self._lock_until = now + locked_for
            self._set_locked(True)
            self._show_error(
                "Too many failed attempts. Try again later."
                if not self._is_arabic()
                else "محاولات كثيرة خاطئة. حاول لاحقًا."
            )
            QTimer.singleShot(locked_for * 1000, self._unlock_after_timeout)
            return

        self._show_error(
            f"Incorrect password. {remaining} attempts remaining."
            if not self._is_arabic()
            else f"كلمة المرور خاطئة. تبقّى {remaining} محاولات."
        )
        self.password_input.clear()
        self.password_input.setFocus()

    def _restore_lockout_state(self):
        remaining = auth.lockout_remaining()
        if not remaining:
            return
        self._set_locked(True)
        self._show_error(
            f"Too many failed attempts. Try again in {remaining} seconds."
            if not self._is_arabic()
            else f"محاولات كثيرة خاطئة. حاول مرة أخرى بعد {remaining} ثانية."
        )
        QTimer.singleShot(remaining * 1000, self._unlock_after_timeout)

    def _set_locked(self, locked: bool):
        self.unlock_btn.setEnabled(not locked)
        self.password_input.setEnabled(not locked)

    def _unlock_after_timeout(self):
        if auth.lockout_remaining():
            return
        self._lock_until = 0.0
        self._set_locked(False)
        self.error_label.setVisible(False)
        self.password_input.setFocus()

    def _on_forgot_password(self):
        if not auth.has_security_question():
            QMessageBox.information(
                self,
                "Recovery",
                "No security question set.\nPlease reset the app if you lost your password."
                if not self._is_arabic()
                else "لا يوجد سؤال أمان.\nيُرجى إعادة تعيين البرنامج إذا فقدت كلمة المرور."
            )
            return

        from PySide6.QtWidgets import QInputDialog

        question = settings.get("security_question")

        answer, ok = QInputDialog.getText(
            self,
            "Security Question",
            question,
            QLineEdit.EchoMode.Normal,
        )
        if not ok or not answer:
            return

        if not auth.verify_security_answer(answer):
            self._show_error(
                "Incorrect answer." if not self._is_arabic() else "الإجابة خاطئة."
            )
            return

        new_pass, ok = QInputDialog.getText(
            self,
            "New Password",
            "Enter new password:" if not self._is_arabic() else "أدخل كلمة المرور الجديدة:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not new_pass:
            return

        confirm, ok = QInputDialog.getText(
            self,
            "Confirm Password",
            "Confirm new password:" if not self._is_arabic() else "أكّد كلمة المرور:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        try:
            auth.reset_password_via_security(answer, new_pass, confirm)
            QMessageBox.information(
                self,
                "Success",
                "Password has been reset. You can now log in."
                if not self._is_arabic()
                else "تم إعادة تعيين كلمة المرور. يمكنك الآن الدخول."
            )
        except AuthError as e:
            self._show_error(str(e))

    # --------------------------------------------------------
    # مساعدات العرض
    # --------------------------------------------------------
    def _show_error(self, message: str):
        self.error_label.setText("⚠ " + message)
        self.error_label.setVisible(True)

    def _show_success_and_continue(self):
        self.error_label.setVisible(False)
        self.login_successful.emit()

    # --------------------------------------------------------
    # الأنماط
    # --------------------------------------------------------
    def closeEvent(self, event):
        guard = getattr(self, "_close_guard", None)
        if guard and not guard():
            event.ignore()
            return
        super().closeEvent(event)

    def _apply_style(self):
        c = self.palette_data
        set_widget_stylesheet(self, f"""
            QWidget#LoginRoot {{
                background-color: {c['bg_base']};
            }}
            QFrame#Card {{
                background-color: {c['bg_surface']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
            QLabel#DeveloperLogo {{
                background: transparent;
                color: {c['primary']};
                font-size: 72px;
                font-weight: 800;
            }}
            QLabel#Divider {{
                color: {c['primary']};
                font-size: 12px;
                letter-spacing: 2px;
            }}
            QLabel#AppTitle {{
                color: {c['text']};
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#FieldLabel {{
                color: {c['text_muted']};
                font-size: 12px;
                font-weight: 500;
            }}
            QLabel#Hint {{
                color: {c['text_muted']};
                font-size: 11px;
            }}
            QLabel#ErrorMsg {{
                color: {c['danger']};
                font-size: 12px;
                padding: 8px;
                background-color: rgba(220, 38, 38, 0.1);
                border-radius: 6px;
            }}
            QLabel#Footer {{
                color: {c['text_muted']};
                font-size: 11px;
            }}
            QPushButton#LinkButton {{
                background: transparent;
                border: none;
                color: {c['primary']};
                font-size: 12px;
                padding: 2px;
            }}
            QPushButton#LinkButton:hover {{
                color: {c['primary_hover']};
                text-decoration: underline;
            }}
            QLineEdit {{
                background-color: {c['bg_elevated']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {c['primary']};
            }}
            QPushButton#Primary {{
                background-color: {c['primary']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton#Primary:hover {{
                background-color: {c['primary_hover']};
            }}
            QPushButton#Primary:pressed {{
                background-color: {c['primary_active']};
            }}
            QPushButton#Primary:disabled {{
                background-color: {c['border']};
                color: {c['text_muted']};
            }}
        """)
        self.password_input.setFocus()
