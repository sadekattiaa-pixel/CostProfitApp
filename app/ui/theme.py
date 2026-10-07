"""
Theme: الألوان والخطوط والأنماط حسب الهوية البصرية.
"""
import re

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication


# ============================================================
# الألوان — الوضع الليلي (الافتراضي)
# ============================================================
DARK = {
    "bg_base":       "#0A1220",
    "bg_surface":    "#0F1D35",
    "bg_elevated":   "#132642",
    "border":        "#1E3A5F",
    "border_subtle": "#162B47",
    "primary":       "#2563EB",
    "primary_hover": "#3B82F6",
    "primary_active":"#1D4ED8",
    "text":          "#FFFFFF",
    "text_muted":    "#94A3B8",
    "success":       "#22C55E",
    "warning":       "#F59E0B",
    "danger":        "#DC2626",
    "info":          "#0EA5E9",
}

# ============================================================
# الألوان — الوضع النهاري
# ============================================================
LIGHT = {
    "bg_base":       "#F8FAFC",
    "bg_surface":    "#FFFFFF",
    "bg_elevated":   "#F1F5F9",
    "border":        "#CBD5E1",
    "border_subtle": "#E2E8F0",
    "primary":       "#2563EB",
    "primary_hover": "#3B82F6",
    "primary_active":"#1D4ED8",
    "text":          "#0F172A",
    "text_muted":    "#475569",
    "success":       "#15803D",
    "warning":       "#B45309",
    "danger":        "#DC2626",
    "info":          "#0284C7",
}



def _light_style(stylesheet: str) -> str:
    """Adapt existing dark page styles while keeping their layout unchanged."""
    c = LIGHT
    token = re.compile(r"#[0-9a-fA-F]{6}\b|rgba?\([^)]*\)")
    declaration = re.compile(r"([a-z-]+)\s*:\s*([^;{}]+)(;|$)", re.I)

    def rgb(value):
        if value.startswith("#"):
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        parts = re.findall(r"[0-9.]+", value)
        return tuple(int(float(part)) for part in parts[:3])

    def adapt_body(selector, body):
        # Keep the navigation rail dark independently of the content theme.
        if any(name in selector for name in (
            "#Sidebar", "#NavButton", "#DevInfoBox", "#DevName",
            "#DevCompany", "#DevContact", "QFrame#Divider",
        )):
            return body
        backgrounds = re.findall(r"(?:background|background-color)\s*:\s*([^;]+)", body)
        filled = any(
            color.startswith("#") and max(rgb(color)) - min(rgb(color)) > 80
            for value in backgrounds for color in token.findall(value)
        ) or ("qlineargradient" in body and "#3B82F6" in body)
        filled = filled or any(name in selector for name in ("#Primary", "#Danger", "#SuccessBtn"))
        filled = filled and not any(name in selector for name in ("SmallDanger", "IconBtnDanger"))
        is_input = any(name in selector for name in (
            "QLineEdit", "QTextEdit", "QPlainTextEdit", "QSpinBox", "QDoubleSpinBox",
            "QComboBox", "QDateEdit", "QAbstractItemView",
        ))

        def adapt_declaration(match):
            prop, value, ending = match.groups()
            if prop in ("background", "background-color") and "qlineargradient" in value:
                if any(max(rgb(color)) < 110 for color in token.findall(value)):
                    return f"{prop}: {c['bg_surface']}{ending}"

            def adapt_color(match):
                color = match.group()
                r, g, b = rgb(color)
                if prop == "selection-color":
                    return "#FFFFFF"
                if prop == "selection-background-color":
                    return c["primary"]
                if prop == "color":
                    if (r, g, b) == (255, 255, 255):
                        return "#FFFFFF" if filled else c["text"]
                    if min(r, g, b) >= 190:
                        return c["text"]
                    if (r, g, b) in ((148, 163, 184), (160, 184, 216)):
                        return c["text_muted"]
                    if (r, g, b) in ((96, 165, 250), (59, 130, 246)):
                        return c["primary_active"]
                    if (r, g, b) in ((248, 113, 113), (239, 68, 68)):
                        return c["danger"]
                    if (r, g, b) == (34, 197, 94):
                        return c["success"]
                    if (r, g, b) == (245, 158, 11):
                        return c["warning"]
                    if (r, g, b) == (14, 165, 233):
                        return c["info"]
                if prop in ("background", "background-color", "alternate-background-color"):
                    if "#SidebarLogoBanner" in selector:
                        return DARK["bg_surface"]
                    if max(r, g, b) < 110:
                        if (r, g, b) == (0, 0, 0):
                            return c["bg_base"]
                        return c["bg_elevated"] if "QHeaderView" in selector else c["bg_surface"]
                    if (r, g, b) == (255, 255, 255):
                        return c["bg_elevated"] if ":hover" in selector else c["bg_surface"]
                    if color.startswith("rgba") and (r, g, b) in ((37, 99, 235), (59, 130, 246)):
                        if "QScrollBar" in selector:
                            return c["border"] if ":hover" not in selector else c["primary"]
                        return "#DBEAFE" if ":selected" in selector or 'active="true"' in selector else "#EFF6FF"
                if prop.startswith("border") or prop == "gridline-color":
                    if (r, g, b) in ((37, 99, 235), (59, 130, 246)):
                        return c["primary"] if any(state in selector for state in (":focus", ":hover", ":selected", 'active="true"')) else c["border"]
                    if max(r, g, b) < 110 or (r, g, b) == (255, 255, 255):
                        return c["border"]
                return color

            value = token.sub(adapt_color, value)
            if prop == "background-color" and is_input and ":disabled" in selector:
                value = c["bg_elevated"]
            return f"{prop}: {value}{ending}"

        return declaration.sub(adapt_declaration, body)

    if "{" not in stylesheet:
        return adapt_body("", stylesheet)
    return re.sub(
        r"([^{}]+)\{([^{}]*)\}",
        lambda match: match[1] + "{" + adapt_body(match[1], match[2]) + "}",
        stylesheet,
    )


def set_widget_stylesheet(widget, stylesheet: str) -> None:
    """Retain the original style so switching back restores the dark colors."""
    widget._theme_stylesheet_source = stylesheet
    app = QApplication.instance()
    theme = app.property("costprofit_theme") if app is not None else None
    if theme is None:
        parent = widget
        while parent is not None and theme is None:
            theme = getattr(parent, "theme", None)
            parent = parent.parentWidget()
    parent = widget
    while parent is not None:
        fixed_theme = getattr(parent, "_fixed_theme", None)
        if fixed_theme is not None:
            theme = fixed_theme
            break
        parent = parent.parentWidget()
    widget.setStyleSheet(_light_style(stylesheet) if theme == "light" else stylesheet)
    if hasattr(widget, "_theme_pixmap_icon"):
        from app.ui.icons import make_icon
        name, color, size = widget._theme_pixmap_icon
        if theme == "light":
            color = _light_style(f"color: {color};").split(":")[1].strip().rstrip(";")
        else:
            color = "#FFFFFF"
        widget.setPixmap(make_icon(name, color=color, size=size).pixmap(size, size))


def get_palette(theme: str = "dark") -> dict:
    """يُرجع لوحة الألوان حسب الوضع."""
    return LIGHT if theme == "light" else DARK


# ============================================================
# الخطوط
# ============================================================
def get_app_font(size: int = 14, weight: int = 400) -> QFont:
    """يُرجع خطًا موحدًا للتطبيق."""
    font = QFont("Segoe UI", size)
    font.setWeight(QFont.Weight(weight) if isinstance(weight, int) else weight)
    return font


def apply_global_font(app: QApplication) -> None:
    """يُطبق الخط الافتراضي على كل التطبيق."""
    font = QFont("Segoe UI", 12)
    app.setFont(font)


# ============================================================
# ورقة الأنماط (QSS) — مطبقة على كل التطبيق
# ============================================================
def build_stylesheet(theme: str = "dark") -> str:
    c = get_palette(theme)
    return f"""
    /* ----- عام ----- */
    QWidget {{
        background-color: {c['bg_base']};
        color: {c['text']};
        font-family: "Segoe UI", "Cairo", "Tahoma", sans-serif;
        font-size: 16px;
    }}

    /* التسميات شفافة افتراضيًا */
    QLabel {{
        background: transparent;
        color: {c['text']};
    }}

    QMainWindow, QDialog {{
        background-color: {c['bg_base']};
    }}

    /* ----- البطاقات ----- */
    QFrame#Card {{
        background-color: {c['bg_surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}

    /* ----- حقول الإدخال ----- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QDateEdit, QComboBox {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 10px 14px;
        min-height: 28px;
        font-size: 16px;
        selection-background-color: {c['primary']};
        selection-color: #FFFFFF;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
        border: 1px solid {c['primary']};
    }}

    QLineEdit:disabled, QComboBox:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {c['text_muted']};
        background-color: {c['bg_surface']};
    }}

    /* ----- الأزرار ----- */
    QPushButton {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 10px 18px;
        min-height: 28px;
        font-size: 16px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: {c['border']};
    }}

    QPushButton:pressed {{
        background-color: {c['primary_active']};
    }}

    QPushButton:disabled {{
        color: {c['text_muted']};
        background-color: {c['bg_surface']};
    }}

    QPushButton#Primary {{
        background-color: {c['primary']};
        color: #FFFFFF;
        border: none;
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

    QPushButton#Danger {{
        background-color: {c['danger']};
        color: #FFFFFF;
        border: none;
    }}

    QPushButton#Danger:hover {{
        background-color: #EF4444;
    }}

    /* ----- الجداول ----- */
    QTableWidget, QTableView {{
        background-color: {c['bg_surface']};
        alternate-background-color: {c['bg_base']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        gridline-color: {c['border_subtle']};
        selection-background-color: {c['primary']};
        selection-color: #FFFFFF;
        font-size: 15px;
    }}

    QHeaderView::section {{
        background-color: {c['bg_surface']};
        color: {c['text_muted']};
        border: none;
        border-bottom: 1px solid {c['border']};
        padding: 12px 10px;
        font-weight: 600;
        font-size: 14px;
    }}

    QTableWidget::item {{
        padding: 10px 8px;
    }}

    /* ----- التمرير ----- */
    QScrollBar:vertical {{
        background-color: {c['bg_base']};
        width: 12px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['border']};
        border-radius: 6px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['primary']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c['bg_base']};
        height: 12px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['border']};
        border-radius: 6px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c['primary']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ----- التبويبات ----- */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 7px;
        background-color: {c['bg_surface']};
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_muted']};
        padding: 12px 22px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 15px;
    }}

    QTabBar::tab:selected {{
        color: {c['text']};
        border-bottom: 2px solid {c['primary']};
    }}

    QTabBar::tab:hover {{
        color: {c['text']};
    }}

    /* ----- التسميات ----- */
    QLabel#Title {{
        font-size: 26px;
        font-weight: 600;
        color: {c['text']};
    }}

    QLabel#Subtitle {{
        font-size: 14px;
        color: {c['text_muted']};
    }}

    QLabel#Muted {{
        color: {c['text_muted']};
    }}

    QLabel#Success {{ color: {c['success']}; }}
    QLabel#Warning {{ color: {c['warning']}; }}
    QLabel#Danger  {{ color: {c['danger']}; }}
    QLabel#Primary {{ color: {c['primary']}; }}

    /* ----- القوائم المنسدلة ----- */
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
        selection-background-color: {c['primary']};
        selection-color: #FFFFFF;
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 6px;
        outline: none;
        font-size: 16px;
    }}

    /* ----- الـ Checkbox ----- */
    QCheckBox {{
        color: {c['text']};
        spacing: 10px;
        font-size: 15px;
    }}

    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 1px solid {c['border']};
        background-color: {c['bg_elevated']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {c['primary']};
        border: 1px solid {c['primary']};
    }}

    /* ----- شريط الأدوات / الحالة ----- */
    QStatusBar {{
        background-color: {c['bg_surface']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        font-size: 13px;
    }}

    /* ----- التلميحات ----- */
    QToolTip {{
        background-color: {c['bg_elevated']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
    }}
    """


class Theme:
    """Compatibility wrapper used by CLI smoke tests and simple terminals."""

    def __init__(self, mode: str = "dark"):
        self.mode = mode.lower() if isinstance(mode, str) else "dark"
        self.palette = get_palette(self.mode)
        self.ICONS = {
            "db": "db",
            "settings": "settings",
            "invoice": "invoice",
            "supplier": "supplier",
            "product": "product",
            "money": "money",
            "security": "security",
            "user": "user",
            "info": "info",
        }

    def _style(self, text: str, ok: bool) -> str:
        status = "OK" if ok else "FAIL"
        return f"[{status}] {text}"

    def header(self, text: str) -> str:
        return f"\n=== {text} ===\n"

    def status(self, text: str, ok: bool = True) -> str:
        return self._style(text, ok)

    def box(self, title: str, lines: list[str]) -> str:
        width = max(len(title), max((len(line) for line in lines), default=0)) + 4
        top = "+" + "-" * width + "+"
        body = [f"| {title:<{width - 4}} |", "|" + " " * (width - 2) + "|"]
        for line in lines:
            body.append(f"| {line:<{width - 4}} |")
        body.append("|" + " " * (width - 2) + "|")
        return "\n".join([top, *body, top])


def apply_theme(app: QApplication, theme: str = "dark") -> None:
    """يُطبق الوضع على التطبيق كاملًا."""
    app.setProperty("costprofit_theme", theme)
    app.setStyleSheet(build_stylesheet(theme))
    apply_global_font(app)
    widgets = list(app.allWidgets())
    for widget in widgets:
        widget_theme = getattr(widget, "_fixed_theme", theme)
        if hasattr(widget, "theme"):
            widget.theme = widget_theme
        if hasattr(widget, "palette_data"):
            widget.palette_data = get_palette(widget_theme)
        if widget.__class__.__name__ == "SettingsPage":
            combo = widget.gen_theme_combo
            blocked = combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(theme))
            combo.blockSignals(blocked)
    for widget in widgets:
        restyle = getattr(widget, "_apply_style", None)
        if widget.__class__.__module__.startswith("app.ui") and callable(restyle):
            restyle()
        elif hasattr(widget, "_theme_stylesheet_source"):
            set_widget_stylesheet(widget, widget._theme_stylesheet_source)
        if hasattr(widget, "_theme_chart_data"):
            widget.set_data(widget._theme_chart_data)
        if hasattr(widget, "nav_buttons"):
            for key, button in widget.nav_buttons.items():
                from app.ui.icons import make_icon
                color = DARK["primary"] if key == widget.current_page else DARK["text_muted"]
                button.setIcon(make_icon(key, color=color, size=26))
            widget.lock_btn.setIcon(make_icon("lock", color=get_palette(theme)["text_muted"], size=20))
        if widget.__class__.__name__ in ("ProductsPage", "SuppliersPage"):
            from app.ui.icons import make_icon
            for name, icon, size in (("refresh_btn", "reports", 16), ("export_btn", "file_edit", 18), ("import_btn", "archive", 18)):
                button = getattr(widget, name, None)
                if button is not None:
                    button.setIcon(make_icon(icon, color=get_palette(theme)["primary"] if theme == "light" else "#FFFFFF", size=size))
        if widget.__class__.__name__ == "InvoicePage":
            from app.ui.icons import make_icon
            widget.save_btn.setIcon(make_icon("invoice", color=get_palette(theme)["primary"] if theme == "light" else "#FFFFFF", size=16))
            for row in widget._item_rows:
                for name in ("code_item", "supplier_item", "category_item", "ah_item", "l_item", "w_item", "h_item", "oh_item", "layout_item"):
                    item = row.get(name)
                    if item is not None:
                        item.setForeground(QColor(get_palette(theme)["text_muted"]) if theme == "light" else QColor("lightGray"))
            widget._recalculate()
        if widget.__class__.__name__ == "ArchivePage":
            widget.refresh()