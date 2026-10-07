"""
مكونات الرسوم البيانية (QtCharts).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QFont, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QPieSlice,
    QLineSeries, QBarSeries, QBarSet, QBarCategoryAxis,
    QValueAxis, QCategoryAxis,
)

from app.ui.theme import get_palette
from app.ui.theme import set_widget_stylesheet


# ============================================================
# Helpers
# ============================================================
def _make_chart_view(chart: QChart) -> QChartView:
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    set_widget_stylesheet(view, "background: transparent;")
    view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return view


def _no_data_widget(message: str = "No data available") -> QLabel:
    lbl = QLabel(message)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    set_widget_stylesheet(lbl, "color: rgba(148,163,184,0.7); font-size: 16px;")
    return lbl


def _get_value(d: dict, *keys) -> float:
    """يستخرج أول قيمة موجودة من المفاتيح."""
    for k in keys:
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                pass
    return 0.0


# ============================================================
# Donut Chart
# ============================================================
class DonutChart(QWidget):
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self.theme = theme
        self.palette_data = get_palette(theme)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._chart_view: QChartView | None = None

    def set_data(self, data: list[dict]):
        self._theme_chart_data = list(data)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data:
            self._layout.addWidget(_no_data_widget("No data for this period"))
            return

        c = self.palette_data
        colors = ["#2563EB", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#0EA5E9"]

        series = QPieSeries()
        series.setHoleSize(0.55)

        total = sum(_get_value(d, "profit", "value") for d in data)

        for i, d in enumerate(data):
            val = _get_value(d, "profit", "value")
            label = d.get("category") or d.get("month") or f"#{i+1}"
            sl = QPieSlice(label, val)
            sl.setColor(QColor(colors[i % len(colors)]))
            sl.setBorderColor(QColor(c["bg_surface"]))
            sl.setBorderWidth(2)
            sl.setLabelVisible(False)
            series.append(sl)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor(c["text_muted"]))
        chart.legend().setFont(QFont("Segoe UI", 10))
        chart.setBackgroundVisible(False)
        chart.setMargins(chart.margins().__class__(0, 0, 0, 0))

        self._chart_view = _make_chart_view(chart)
        self._layout.addWidget(self._chart_view, 1)


# ============================================================
# Line Chart — يقبل value أو profit
# ============================================================
class ProfitLineChart(QWidget):
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self.theme = theme
        self.palette_data = get_palette(theme)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def set_data(self, data: list[dict]):
        self._theme_chart_data = list(data)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data:
            self._layout.addWidget(_no_data_widget("No profit data yet"))
            return

        c = self.palette_data

        series = QLineSeries()
        series.setColor(QColor(c["primary"]))
        pen = QPen(QColor(c["primary"]))
        pen.setWidth(3)
        series.setPen(pen)

        max_y = 0
        for i, d in enumerate(data):
            val = _get_value(d, "value", "profit")
            series.append(i, val)
            if val > max_y:
                max_y = val

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        chart.setMargins(chart.margins().__class__(10, 10, 10, 10))

        axis_x = QCategoryAxis()
        axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPosition.AxisLabelsPositionOnValue)
        for i, d in enumerate(data):
            label = str(d.get("month") or d.get("date") or i)
            if len(label) > 6:
                label = label[-5:]
            axis_x.append(label, i)
        axis_x.setRange(-0.5, len(data) - 0.5)
        axis_x.setLabelsColor(QColor(c["text_muted"]))
        axis_x.setLinePenColor(QColor(c["border"]))
        axis_x.setGridLineVisible(False)
        axis_x.setLabelsFont(QFont("Segoe UI", 9))

        axis_y = QValueAxis()
        axis_y.setRange(0, max_y * 1.2 if max_y > 0 else 1)
        axis_y.setLabelsColor(QColor(c["text_muted"]))
        axis_y.setLinePenColor(QColor(c["border"]))
        axis_y.setGridLineColor(QColor(c["border_subtle"]))
        axis_y.setLabelsFont(QFont("Segoe UI", 9))
        axis_y.setLabelFormat("%.0f")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self._layout.addWidget(_make_chart_view(chart), 1)


# ============================================================
# Bar Chart
# ============================================================
class PaymentsVsProfitChart(QWidget):
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self.theme = theme
        self.palette_data = get_palette(theme)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def set_data(self, data: list[dict]):
        self._theme_chart_data = list(data)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data:
            self._layout.addWidget(_no_data_widget("No data for this period"))
            return

        c = self.palette_data

        set_payments = QBarSet("Payments")
        set_payments.setColor(QColor(c["primary"]))
        set_payments.setBorderColor(QColor(c["primary"]))

        set_profit = QBarSet("Profit")
        set_profit.setColor(QColor(c["success"]))
        set_profit.setBorderColor(QColor(c["success"]))

        categories = []
        max_y = 0
        for d in data:
            payments = _get_value(d, "payments")
            profit = _get_value(d, "profit", "value")
            set_payments.append(payments)
            set_profit.append(profit)
            label = str(d.get("month") or d.get("date") or "")
            if len(label) > 6:
                label = label[-5:]
            categories.append(label)
            max_y = max(max_y, payments, profit)

        series = QBarSeries()
        series.append(set_payments)
        series.append(set_profit)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor(c["text_muted"]))
        chart.legend().setFont(QFont("Segoe UI", 10))
        chart.setBackgroundVisible(False)
        chart.setMargins(chart.margins().__class__(10, 10, 10, 10))

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor(c["text_muted"]))
        axis_x.setLinePenColor(QColor(c["border"]))
        axis_x.setGridLineVisible(False)
        axis_x.setLabelsFont(QFont("Segoe UI", 9))

        axis_y = QValueAxis()
        axis_y.setRange(0, max_y * 1.2 if max_y > 0 else 1)
        axis_y.setLabelsColor(QColor(c["text_muted"]))
        axis_y.setLinePenColor(QColor(c["border"]))
        axis_y.setGridLineColor(QColor(c["border_subtle"]))
        axis_y.setLabelsFont(QFont("Segoe UI", 9))
        axis_y.setLabelFormat("%.0f")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self._layout.addWidget(_make_chart_view(chart), 1)