"""Reusable PDF preview, save, and print dialog."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSizeF, Qt
import shiboken6

BACK_TO_OPTIONS = 2
from PySide6.QtGui import QPainter, QPageLayout, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout,
)


class PdfPreviewDialog(QDialog):
    def __init__(self, parent, pdf_path: str | Path, language="en",
                 suggested_name="document.pdf", allow_options=False):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.language = language
        self.suggested_name = suggested_name
        self.setWindowTitle("معاينة الطباعة" if language == "ar" else "Print Preview")
        self.resize(1100, 780)
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.page_label = QLabel()
        toolbar.addWidget(self.page_label)
        toolbar.addStretch()

        zoom_out = QPushButton("−")
        zoom_out.clicked.connect(lambda: self._zoom(0.85))
        toolbar.addWidget(zoom_out)
        zoom_in = QPushButton("+")
        zoom_in.clicked.connect(lambda: self._zoom(1.15))
        toolbar.addWidget(zoom_in)
        fit_btn = QPushButton("ملاءمة العرض" if language == "ar" else "Fit width")
        fit_btn.clicked.connect(self._fit_width)
        toolbar.addWidget(fit_btn)
        save_btn = QPushButton("حفظ PDF" if language == "ar" else "Save PDF")
        save_btn.clicked.connect(self._save_copy)
        toolbar.addWidget(save_btn)
        print_btn = QPushButton("طباعة" if language == "ar" else "Print")
        print_btn.clicked.connect(self._print)
        toolbar.addWidget(print_btn)
        if allow_options:
            back_btn = QPushButton("العودة إلى خيارات الطباعة" if language == "ar" else "Back to print options")
            back_btn.clicked.connect(lambda: self.done(BACK_TO_OPTIONS))
            toolbar.addWidget(back_btn)
        close_btn = QPushButton("إغلاق" if language == "ar" else "Close")
        close_btn.clicked.connect(self.accept)
        toolbar.addWidget(close_btn)
        layout.addLayout(toolbar)

        self.document = QPdfDocument(self)
        self.pdf_buffer = QBuffer(self)
        self.pdf_buffer.setData(QByteArray(self.pdf_path.read_bytes()))
        self.pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.document.load(self.pdf_buffer)
        error = self.document.error()
        if error != QPdfDocument.Error.None_:
            raise RuntimeError(f"Unable to load PDF preview: {error}")

        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        layout.addWidget(self.view, 1)
        self.page_label.setText(
            (f"عدد الصفحات: {self.document.pageCount()}" if language == "ar"
             else f"Pages: {self.document.pageCount()}")
        )
        self._fit_width()

    def _fit_width(self):
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _zoom(self, factor):
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(max(0.2, min(5.0, self.view.zoomFactor() * factor)))

    def _save_copy(self):
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ PDF" if self.language == "ar" else "Save PDF",
            self.suggested_name,
            "PDF (*.pdf)",
        )
        if not destination:
            return
        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
        shutil.copy2(self.pdf_path, destination)
        QMessageBox.information(
            self,
            "تم الحفظ" if self.language == "ar" else "Saved",
            destination,
        )

    def _print(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        try:
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            target_size = page_rect.size().toSize()
            for page in range(self.document.pageCount()):
                if page:
                    printer.newPage()
                image = self.document.render(page, target_size)
                painter.drawImage(page_rect, image)
        finally:
            painter.end()


def show_pdf_preview(parent, pdf_path: str | Path, language="en",
                     suggested_name="document.pdf", allow_options=False) -> int:
    dialog = PdfPreviewDialog(parent, pdf_path, language, suggested_name, allow_options)
    try:
        return dialog.exec()
    finally:
        # Dispose the view before its document; passing None makes Qt reconnect to a null document.
        shiboken6.delete(dialog.view)
        dialog.document.close()
        shiboken6.delete(dialog)
