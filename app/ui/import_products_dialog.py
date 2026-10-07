from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.excel_product_import import ExcelProductImporter
from app.config import CATEGORIES, CATEGORIES_AR
from app.ui.theme import build_stylesheet
from app.ui.theme import set_widget_stylesheet


class ImportProductsDialog(QDialog):
    HEADERS_EN = ["Product", "Pattern", "Category", "Supplier", "AH", "L", "W", "H", "OH", "layout", "Pallet"]
    HEADERS_AR = ["Product", "النقشة", "التصنيف", "المورد", "AH", "L", "W", "H", "OH", "layout", "Pallet"]

    def __init__(self, parent=None, language="en", theme="dark"):
        super().__init__(parent)
        self.language = language
        self.theme = theme
        self.file_path = ""
        self.report = None
        self.setWindowTitle(self._text("Import Products from Excel", "استيراد أصناف من Excel"))
        self.resize(1100, 650)
        set_widget_stylesheet(self, build_stylesheet(theme))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText(self._text("Choose an Excel workbook...", "اختر ملف Excel..."))
        file_row.addWidget(self.path_edit, 1)

        self.choose_btn = QPushButton(self._text("Choose File", "اختيار الملف"))
        self.choose_btn.setObjectName("Primary")
        self.choose_btn.clicked.connect(self.choose_file)
        file_row.addWidget(self.choose_btn)

        self.template_btn = QPushButton(self._text("Download Template", "تنزيل القالب"))
        self.template_btn.setObjectName("Secondary")
        self.template_btn.clicked.connect(self.download_template)
        file_row.addWidget(self.template_btn)
        layout.addLayout(file_row)

        self.info_label = QLabel(self._text(
            "Batteries: code and specifications. Tires: name and pattern. Category and supplier are required.",
            "البطاريات: الكود والمواصفات. الإطارات: الاسم والنقشة. التصنيف والمورد مطلوبان.",
        ))
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, len(self.HEADERS_EN))
        self.table.setHorizontalHeaderLabels(self.HEADERS_AR if language == "ar" else self.HEADERS_EN)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.errors_label = QLabel()
        self.errors_label.setWordWrap(True)
        self.errors_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.errors_label.setVisible(False)
        layout.addWidget(self.errors_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton(self._text("Close", "إغلاق"))
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_btn)
        self.import_btn = QPushButton(self._text("Import Products", "استيراد الأصناف"))
        self.import_btn.setObjectName("Primary")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.import_data)
        buttons.addWidget(self.import_btn)
        layout.addLayout(buttons)

    def _text(self, en, ar):
        return ar if self.language == "ar" else en

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("Choose Excel File", "اختر ملف Excel"),
            "",
            "Excel Workbooks (*.xlsx)",
        )
        if not path:
            return
        self.file_path = path
        self.path_edit.setText(path)
        self._load_preview()

    def _load_preview(self):
        self.report = ExcelProductImporter.import_file(self.file_path)
        self.table.setRowCount(len(self.report.rows))
        category_map = dict(zip(CATEGORIES, CATEGORIES_AR))
        keys = ("code", "pattern", "category", "supplier", "ah", "l", "w", "h", "oh", "layout", "pallet")
        for row_index, row in enumerate(self.report.rows):
            for column, key in enumerate(keys):
                value = getattr(row, key)
                if key == "category" and self.language == "ar":
                    value = category_map.get(value, value)
                cell = QTableWidgetItem("" if value is None else str(value))
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_index, column, cell)

        self.import_btn.setEnabled(bool(self.report.rows))
        error_count = len(self.report.errors)
        self.info_label.setText(self._text(
            f"Preview: {len(self.report.rows)} valid rows, {error_count} row errors.",
            f"المعاينة: {len(self.report.rows)} صف صالح، و{error_count} أخطاء.",
        ))
        self.errors_label.setText("\n".join(self.report.errors))
        self.errors_label.setVisible(bool(self.report.errors))

    def import_data(self):
        if not self.file_path:
            return
        self._load_preview()
        if not self.report.rows:
            QMessageBox.warning(
                self,
                self._text("Import", "الاستيراد"),
                self._text("No valid product rows were found.", "لم يتم العثور على صفوف أصناف صالحة."),
            )
            return

        created, errors = ExcelProductImporter.save_to_database(self.report)
        self.info_label.setText(self._text(
            f"Imported {created} product(s); {len(errors)} issue(s).",
            f"تم استيراد {created} صنف؛ عدد الملاحظات {len(errors)}.",
        ))
        self.errors_label.setText("\n".join(errors))
        self.errors_label.setVisible(bool(errors))
        result_text = self._text(
            f"Imported {created} product(s); {len(errors)} row(s) skipped or failed.",
            f"تم حفظ {created} صنف؛ تعذر حفظ أو تم تخطي {len(errors)} صف.",
        )
        if errors:
            visible_errors = errors[:10]
            result_text += "\n\n" + "\n".join(visible_errors)
            if len(errors) > len(visible_errors):
                result_text += self._text(
                    f"\n... and {len(errors) - len(visible_errors)} more.",
                    f"\n... و{len(errors) - len(visible_errors)} أخطاء أخرى.",
                )
        if created:
            QMessageBox.information(
                self,
                self._text("Import Complete", "اكتمل الاستيراد"),
                result_text,
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                self._text("No Products Imported", "لم يتم استيراد أصناف"),
                result_text + "\n\n" + self._text(
                    "Review the row errors and correct the workbook.",
                    "راجع أخطاء الصفوف وصحح الملف.",
                ),
            )

    def download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._text("Save Product Template", "حفظ قالب الأصناف"),
            "products_template.xlsx",
            "Excel Workbooks (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            ExcelProductImporter.generate_template(path)
            QMessageBox.information(
                self,
                self._text("Template Saved", "تم حفظ القالب"),
                self._text(f"Template saved to:\n{path}", f"تم حفظ القالب في:\n{path}"),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._text("Error", "خطأ"),
                self._text(f"Could not create template: {exc}", f"تعذر إنشاء القالب: {exc}"),
            )