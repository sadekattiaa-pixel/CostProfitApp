"""Read-only device binding inspector; activation happens at first launch."""
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
from app.services.license_service import read_device_binding


class ActivatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invoice — معلومات ربط الجهاز")
        self.resize(620, 240)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        self.status = QLabel("التفعيل تلقائي عند أول تشغيل. هذه الأداة تعرض السجل فقط ولا تنشئ تراخيص أو تلغي الربط.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        button = QPushButton("فحص سجل التفعيل")
        button.clicked.connect(self.inspect)
        layout.addWidget(button)

    def inspect(self):
        selected, _ = QFileDialog.getOpenFileName(self, "اختر License/device.dat من مجلد البرنامج", "", "Device record (*.dat)")
        if not selected:
            return
        try:
            record = read_device_binding(Path(selected))
            self.status.setText(f"مرتبط بهذا الكمبيوتر\nرقم النسخة: {record['copy_id']}\nتاريخ التفعيل: {record['activated_at']}")
        except Exception as exc:
            QMessageBox.warning(self, "Invoice", str(exc))


def main():
    app = QApplication(sys.argv)
    window = ActivatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
