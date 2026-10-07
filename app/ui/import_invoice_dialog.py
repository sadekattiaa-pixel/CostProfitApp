from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QMessageBox,
)

from app.services.excel_invoice_import import ExcelInvoiceImporter
from app.ui.theme import build_stylesheet
from app.ui.theme import set_widget_stylesheet


class ImportInvoiceDialog(QDialog):
    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self.theme = theme
        self.file_path = ""
        self.setWindowTitle("استيراد فاتورة من Excel")
        self.resize(1000, 600)
        set_widget_stylesheet(self, build_stylesheet(theme))

        self.main_layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("اختر ملف Excel...")

        self.select_btn = QPushButton("اختيار الملف")
        self.select_btn.setObjectName("Primary")

        self.import_btn = QPushButton("استيراد")
        self.import_btn.setObjectName("Primary")

        self.template_btn = QPushButton("إنشاء نموذج Excel")
        self.template_btn.setObjectName("Secondary")

        top_layout.addWidget(self.path_edit)
        top_layout.addWidget(self.select_btn)
        top_layout.addWidget(self.import_btn)
        top_layout.addWidget(self.template_btn)

        self.main_layout.addLayout(top_layout)

        self.info_label = QLabel("لم يتم اختيار ملف.")
        self.main_layout.addWidget(self.info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "رقم الفاتورة",
            "التاريخ",
            "المورد",
            "المنتج",
            "Pallet",
            "Qty",
            "سعر الوحدة",
            "التصنيف",
        ])
        self.main_layout.addWidget(self.table)

        self.select_btn.clicked.connect(self.choose_file)
        self.import_btn.clicked.connect(self.import_data)
        self.template_btn.clicked.connect(self.generate_template)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف Excel",
            "",
            "Excel Files (*.xlsx *.xls)"
        )

        if not path:
            return

        self.file_path = path
        self.path_edit.setText(path)

        report = ExcelInvoiceImporter.import_file(path)
        self._load_preview(report)

    def _load_preview(self, report):
        self.table.setRowCount(0)
        rows = report.rows
        self.table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            values = [
                row.invoice_no,
                row.date,
                row.supplier,
                row.product,
                "" if row.pallet is None else str(row.pallet),
                str(row.qty),
                str(row.unit_price),
                row.category,
            ]
            for j, value in enumerate(values):
                self.table.setItem(i, j, QTableWidgetItem(value))

        if report.errors:
            QMessageBox.warning(self, "تنبيه", "\n".join(report.errors))

        self.info_label.setText(
            f"تم تحميل {len(rows)} سطرًا. عدد الأخطاء: {len(report.errors)}"
        )

    def import_data(self):
        if not self.file_path:
            QMessageBox.warning(self, "تنبيه", "اختر ملف Excel أولاً.")
            return

        report = ExcelInvoiceImporter.import_file(self.file_path)

        if report.errors:
            QMessageBox.warning(self, "لم يتم الاستيراد", "لم يتم استيراد أي فاتورة:\n" + "\n".join(report.errors))
            return

        if not report.rows:
            QMessageBox.information(self, "المعلومة", "لم يتم العثور على بيانات صالحة.")
            return

        try:
            saved = ExcelInvoiceImporter.save_report_to_db(report)
            QMessageBox.information(self, "نجاح", f"تم حفظ {saved} فاتورة في قاعدة البيانات بنجاح.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"فشل حفظ البيانات: {exc}")

    def generate_template(self):
        target, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ نموذج Excel",
            "invoice_template.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not target:
            return

        try:
            ExcelInvoiceImporter.generate_template(target)
            QMessageBox.information(self, "نجاح", f"تم إنشاء نموذج Excel في:\n{target}")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء النموذج: {exc}")
