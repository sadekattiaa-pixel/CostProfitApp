
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

class PageControls(QWidget):
    """Bound table widgets to one SQL page without limiting exports."""
    size = 100

    def __init__(self, refresh, parent=None):
        super().__init__(parent)
        self.page = self.total = 0
        self.signature = None
        self.refresh = refresh
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.previous = QPushButton()
        self.next = QPushButton()
        self.label = QLabel()
        for button in (self.previous, self.next):
            button.setObjectName("SecondaryBtn")
            button.setMinimumHeight(34)
        self.previous.clicked.connect(lambda: self.move(-1))
        self.next.clicked.connect(lambda: self.move(1))
        layout.addWidget(self.previous)
        layout.addWidget(self.label)
        layout.addWidget(self.next)
        layout.addStretch()

    @property
    def offset(self):
        return self.page * self.size

    def configure(self, filters, total, language):
        signature = tuple(sorted(filters.items()))
        if signature != self.signature:
            self.page = 0
            self.signature = signature
        self.total = total
        pages = max(1, (total + self.size - 1) // self.size)
        self.page = min(self.page, pages - 1)
        ar = language == 'ar'
        self.previous.setText('السابق' if ar else 'Previous')
        self.next.setText('التالي' if ar else 'Next')
        self.label.setText(f"{self.page + 1} / {pages}")
        self.previous.setEnabled(self.page > 0)
        self.next.setEnabled(self.page + 1 < pages)

    def move(self, delta):
        self.page = max(0, min(self.page + delta, max(0, (self.total - 1) // self.size)))
        self.refresh()
