"""Invoice startup and durable manual OneDrive session handoff."""
import sys
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.config import APP_NAME
from app.db import db
from app.paths import get_shared_db_path, get_shared_images_dir
from app.services.lock_service import lock, acquire_manual_session
from app.services.settings_service import settings
from app.services.error_logging import configure_error_logging, get_error_logger
from app.services.license_service import LicenseError, verify_device_license
from app.services.backup_service import backup_service
from app.storage_config import (
    RESTART_EXIT_CODE, ensure_storage_is_writable, is_storage_configured,
    update_storage_config, LocalDataSession, RecoveryRequired, SessionSaveCoordinator,
)
from app.ui.theme import apply_theme
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "app_icon.ico")))
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Alintilqa.Invoice")
    try:
        verify_device_license()
    except LicenseError as exc:
        QMessageBox.critical(None, "تفعيل Invoice", str(exc))
        return 2

    if not is_storage_configured():
        QMessageBox.information(
            None, "مجلد بيانات Invoice",
            "اختر مجلد البيانات والصور المشترك داخل OneDrive. "
            "على الأجهزة الأخرى اختر المجلد نفسه بعد اكتمال تنزيله. "
            "سجل التفعيل والنسخ الاحتياطية سيبقيان محليًا.",
        )
        selected = QFileDialog.getExistingDirectory(None, "اختر مجلد البيانات والصور", str(Path.home()))
        if not selected:
            return 0
        try:
            update_storage_config(data_dir=selected)
        except Exception as exc:
            QMessageBox.warning(None, "تعذر حفظ المجلد", str(exc))
            return 1
    try:
        ensure_storage_is_writable()
        configure_error_logging()
    except Exception as exc:
        QMessageBox.critical(None, "تعذر استخدام مجلد البيانات", str(exc))
        return 1
    logger = get_error_logger("startup")
    if not acquire_manual_session():
        return 1
    session = LocalDataSession(get_shared_db_path(), get_shared_images_dir())
    opened = False
    safe_to_release = False
    heartbeat_timer = QTimer(app)
    heartbeat_timer.timeout.connect(lock.heartbeat)
    heartbeat_timer.start(30_000)
    exit_code = 1
    previous_sigint = None
    save_coordinator = None
    signal_timer = QTimer(app)
    signal_timer.timeout.connect(lambda: None)
    try:
        try:
            path = session.prepare()
        except RecoveryRequired as exc:
            if session.metadata.get("state") != "active" or not session.local_db.exists():
                raise
            dialog = QMessageBox()
            dialog.setWindowTitle("استعادة العمل المحلي")
            dialog.setText(str(exc))
            dialog.setInformativeText("يمكن استعادة الجلسة إذا لم تتغير البيانات المشتركة، أو حفظها في نسخة احتياطية محلية وبدء العمل بالبيانات المشتركة الحالية.")
            recover_button = dialog.addButton("استعادة العمل المحلي", QMessageBox.ButtonRole.AcceptRole)
            fresh_button = dialog.addButton("حفظ العمل القديم وفتح البيانات المشتركة", QMessageBox.ButtonRole.ActionRole)
            cancel_button = dialog.addButton("إلغاء", QMessageBox.ButtonRole.RejectRole)
            dialog.setDefaultButton(cancel_button)
            dialog.exec()
            if dialog.clickedButton() == recover_button:
                path = session.prepare(recover=True)
            elif dialog.clickedButton() == fresh_button:
                archive_path = session.archive_pending()
                QMessageBox.information(None, "حُفظ العمل السابق", f"نسخة العمل غير المنشورة محفوظة للمراجعة في: {archive_path}")
                path = session.prepare()
            else:
                safe_to_release = True
                return 1
        db.connect(path)
        opened = True
        settings.clear_cache()
        from app.services.product_service import product_service
        product_service.reset_legacy_layout_images()
        if settings.get_bool("safety_copy_on_open", True):
            try:
                backup_service.create_backup(prefix="auto", keep=settings.get_int("backup_keep_count", 30))
            except Exception:
                logger.exception("Failed to create local startup backup")
        apply_theme(app, settings.get("theme") or "dark")
        save_coordinator = SessionSaveCoordinator(session, db, lock, app)
        login = LoginWindow()
        main_window = None

        def on_login_success():
            nonlocal main_window
            if not lock._held:
                QMessageBox.warning(login, "Invoice", "فُقد حجز الجلسة. أغلق البرنامج لاستعادة العمل المحلي.")
                return
            main_window = MainWindow()
            save_coordinator.on_state_changed = main_window.update_save_status
            main_window.update_save_status(save_coordinator.state, save_coordinator.error)
            main_window.showMaximized()
            login.close()

        login.login_successful.connect(on_login_success)
        login.showMaximized()
        previous_sigint = signal.signal(signal.SIGINT, lambda *_: app.quit())
        signal_timer.start(250)
        exit_code = app.exec()
        heartbeat_timer.stop()
        save_coordinator.stop()
        session.publish(db, lock)
        safe_to_release = True
    except Exception as exc:
        logger.exception("Invoice session did not finish")
        QMessageBox.critical(
            None, "لم يكتمل حفظ الجلسة", str(exc) + f"\nنسخة العمل المحلية: {session.directory}\n"
            "لن يُحرر القفل تلقائيًا إذا بدأت الجلسة. لا تنتقل إلى جهاز آخر قبل استعادة العمل.",
        )
        if not opened:
            safe_to_release = True
        exit_code = 1
    finally:
        if save_coordinator:save_coordinator.stop()
        signal_timer.stop()
        if previous_sigint is not None:
            signal.signal(signal.SIGINT, previous_sigint)
        heartbeat_timer.stop()
        db.close()
        session.finish()
        if safe_to_release:
            lock.release()
    if exit_code == RESTART_EXIT_CODE:
        restart_args = list(sys.argv[1:])
        if not getattr(sys, "frozen", False):
            restart_args.insert(0, str(Path(__file__).resolve()))
        QProcess.startDetached(sys.executable, restart_args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
