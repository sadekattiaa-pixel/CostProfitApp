"""
صفحة إدارة الأصناف.
"""
import json
from datetime import date
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QMessageBox, QFileDialog, QScrollArea, QApplication,
)

from app.config import CATEGORIES, CATEGORIES_AR
from app.services.product_service import product_service, ProductError
from app.services.export_service import export_service
from app.services.supplier_service import supplier_service
from app.services.settings_service import settings
from app.ui.theme import get_palette
from app.ui.icons import make_icon
from app.ui.import_products_dialog import ImportProductsDialog
from app.ui.theme import set_widget_stylesheet


# ترتيب الأعمدة الجديد
# (key, en, ar, default_width)
PRODUCT_COLUMNS = [
    ("num",       "#",          "#",          50),
    ("code",      "Product", "Product", 180),
    ("pattern",   "Pattern",    "النقشة",      140),
    ("ah",        "AH",         "AH",         70),
    ("l",         "L",          "L",          70),
    ("w",         "W",          "W",          70),
    ("h",         "H",          "H",          70),
    ("oh",        "OH",         "OH",         70),
    ("layout",    "layout",     "layout",    90),
    ("image",     "layout",      "layout",     70),
    ("category",  "Category",   "التصنيف",    140),
    ("supplier",  "Supplier",   "المورد",     200),
    ("actions",   "Actions",    "إجراءات",    150),
]

PRODUCT_COL_KEYS = [c[0] for c in PRODUCT_COLUMNS]
PRODUCT_DEFAULT_WIDTHS = {c[0]: c[3] for c in PRODUCT_COLUMNS}


TEXTS = {
    "title":         ("Products",                        "الأصناف"),
    "subtitle":      ("Manage your products catalog.",   "إدارة قائمة الأصناف."),
    "btn_new":       ("+ New Product",                   "+ صنف جديد"),
    "btn_import":    ("Import Excel",                    "استيراد Excel"),
    "btn_export":    ("Export Excel",                    "تصدير Excel"),
    "btn_refresh":   ("Refresh",                         "تحديث"),
    "search_ph":     ("Search by code, tire name, pattern, or supplier...",
                      "ابحث بكود الصنف أو اسم الإطار أو النقشة أو المورد..."),
    "filter_cat":    ("All Categories",                  "كل التصنيفات"),
    "filter_sup":    ("All Suppliers",                   "كل الموردين"),
    "sort_name_asc":  ("Code / Name A–Z", "الكود / الاسم أ–ي"),
    "sort_name_desc": ("Code / Name Z–A", "الكود / الاسم ي–أ"),
    "sort_newest":   ("Newest",                          "الأحدث"),
    "sort_code":     ("Code",                            "الكود"),
    "sort_supplier": ("Supplier",                        "المورد"),
    "count":         ("{n} product(s)",                  "{n} صنف"),
    "no_data":       ("No products yet",                 "لا توجد أصناف بعد"),
    "no_data_sub":   ("Click 'New Product' to add your first one.",
                      "اضغط على 'صنف جديد' لإضافة أول صنف."),
    "no_results":    ("No results found",                "لا نتائج"),
    "no_results_sub":("Try a different search term.",    "جرّب كلمة بحث مختلفة."),
    "dlg_new_title": ("New Product",                     "صنف جديد"),
    "dlg_edit_title":("Edit Product",                    "تعديل صنف"),
    "dlg_sub":       ("Add a new product to your catalog.",
                      "أضف صنفًا جديدًا إلى قائمتك."),
    "dlg_sub_edit":  ("Update product information.",
                      "حدّث بيانات الصنف."),
    "tab_specs":     ("Specifications",                  "المواصفات"),
    "field_name":    ("Product *", "Product *"),
    "field_pattern": ("Pattern *", "النقشة *"),
    "err_pattern_req": ("Tire pattern is required.", "نقشة الإطار مطلوبة."),
    "field_code":    ("Product *", "Product *"),
    "field_category":("Category *",                      "التصنيف *"),
    "field_supplier":("Supplier *",                      "المورد *"),
    "field_image":   ("layout",                    "layout"),
    "field_ah":      ("AH",                              "AH"),
    "field_l":       ("L",                               "L"),
    "field_w":       ("W",                               "W"),
    "field_h":       ("H",                               "H"),
    "field_oh":      ("OH",                              "OH"),
    "field_layout":  ("layout",                     "layout"),
    "field_pallet":  ("Pallet",                 "Pallet"),
    "btn_cancel":    ("Cancel",                          "إلغاء"),
    "btn_save":      ("Save",                            "حفظ"),
    "btn_update":    ("Update",                          "تحديث"),
    "upload_img":    ("Upload Image",                    "رفع صورة"),
    "remove_img":    ("Remove",                          "حذف"),
    "no_img":        ("No image",                        "لا توجد صورة"),
    "img_hint":      ("JPG/PNG, max 1.5 MB",             "JPG/PNG، حد أقصى 1.5 MB"),
    "details_title": ("Product Details",                 "تفاصيل الصنف"),
    "spec_section":  ("Specifications",                  "المواصفات"),
    "btn_close":     ("Close",                           "إغلاق"),
    "confirm_delete_t": ("Delete Product",               "حذف الصنف"),
    "confirm_delete_m": ("Are you sure you want to delete \"{name}\"?\nThis cannot be undone.",
                         "هل تريد حذف \"{name}\"؟\nلا يمكن التراجع."),
    "err_title":     ("Error",                           "خطأ"),
    "err_code_req":  ("Product code is required.",       "كود الصنف مطلوب."),
    "err_supplier":  ("Please select a supplier.",       "الرجاء اختيار مورد."),
}


def _t(key, language, **kwargs):
    en, ar = TEXTS.get(key, ("", ""))
    text = ar if language == "ar" else en
    if kwargs:
        text = text.format(**kwargs)
    return text


def _category_label(cat, language):
    if language == "ar":
        try:
            return CATEGORIES_AR[CATEGORIES.index(cat)]
        except ValueError:
            return cat
    return cat


def _fmt_num(v):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def _screen_max_height():
    try:
        s = QApplication.primaryScreen()
        if s:
            return max(500, s.availableGeometry().height() - 80)
    except Exception:
        pass
    return 700


# ============================================================
# نافذة الإضافة/التعديل
# ============================================================
class ProductDialog(QDialog):
    def __init__(self, parent=None, language="en", theme="dark",
                 product=None, preselected_supplier_id=None):
        super().__init__(parent)
        self.language = language
        self.theme = theme
        self.palette_data = get_palette(theme)
        self.product = product
        self.preselected_supplier_id = preselected_supplier_id
        self._temp_image_path = None
        self._image_removed = False
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        is_edit = self.product is not None
        title_key = "dlg_edit_title" if is_edit else "dlg_new_title"
        self.setWindowTitle(_t(title_key, self.language))
        self.setModal(True)
        max_h = _screen_max_height()
        self.setMinimumWidth(700)
        self.setMinimumHeight(480)
        self.resize(720, min(600, max_h))
        self.setMaximumHeight(max_h)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 12)
        hl.setSpacing(4)
        title = QLabel(_t(title_key, self.language))
        title.setObjectName("DialogTitle")
        hl.addWidget(title)
        sub = QLabel(_t("dlg_sub_edit" if is_edit else "dlg_sub", self.language))
        sub.setObjectName("DialogSub")
        hl.addWidget(sub)
        sep = QFrame(); sep.setFixedHeight(1); sep.setObjectName("Sep")
        hl.addWidget(sep)
        root.addWidget(header)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)

        body = QWidget()
        body.setObjectName("DialogBody")
        scroll.setWidget(body)

        body_outer = QHBoxLayout(body)
        body_outer.setContentsMargins(28, 14, 28, 14)
        body_outer.setSpacing(20)

        # Left
        left = QVBoxLayout()
        left.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.code_input = QLineEdit()
        self.identity_label = QLabel(_t("field_code", self.language))
        form.addRow(self.identity_label, self.code_input)
        self.pattern_input = QLineEdit()
        form.addRow(_t("field_pattern", self.language), self.pattern_input)
        self._identity_form = form

        self.cat_combo = QComboBox()
        for cat in CATEGORIES:
            self.cat_combo.addItem(_category_label(cat, self.language), cat)
        form.addRow(_t("field_category", self.language), self.cat_combo)

        self.sup_combo = QComboBox()
        self._load_suppliers()
        form.addRow(_t("field_supplier", self.language), self.sup_combo)

        left.addLayout(form)

        specs_label = QLabel(_t("tab_specs", self.language))
        specs_label.setObjectName("SectionLabel")
        self._specs_label = specs_label
        left.addWidget(specs_label)

        specs_grid = QFormLayout()
        specs_grid.setSpacing(10)
        specs_grid.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ah_input = QLineEdit(); self.ah_input.setPlaceholderText("—")
        specs_grid.addRow(_t("field_ah", self.language), self.ah_input)
        self.l_input = QLineEdit(); self.l_input.setPlaceholderText("—")
        specs_grid.addRow(_t("field_l", self.language), self.l_input)
        self.w_input = QLineEdit(); self.w_input.setPlaceholderText("—")
        specs_grid.addRow(_t("field_w", self.language), self.w_input)
        self.h_input = QLineEdit(); self.h_input.setPlaceholderText("—")
        specs_grid.addRow(_t("field_h", self.language), self.h_input)
        self.oh_input = QLineEdit(); self.oh_input.setPlaceholderText("—")
        specs_grid.addRow(_t("field_oh", self.language), self.oh_input)
        self.layout_input = QLineEdit(); self.layout_input.setPlaceholderText("12")
        specs_grid.addRow(_t("field_layout", self.language), self.layout_input)
        self.pallet_input = QLineEdit(); self.pallet_input.setPlaceholderText("24")
        specs_grid.addRow(_t("field_pallet", self.language), self.pallet_input)

        self._specs_grid = specs_grid
        left.addLayout(specs_grid)
        left.addStretch()
        body_outer.addLayout(left, 3)

        # Right: image
        right = QVBoxLayout()
        right.setSpacing(8)
        img_label = QLabel(_t("field_image", self.language))
        img_label.setObjectName("SectionLabel")
        right.addWidget(img_label)

        self.image_box = QLabel()
        self.image_box.setObjectName("ImageBox")
        self.image_box.setFixedSize(160, 160)
        self.image_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_box.setText(_t("no_img", self.language))
        right.addWidget(self.image_box)

        self.layout_image_combo = QComboBox()
        self.layout_image_combo.addItem("بدون صورة" if self.language == "ar" else "No layout", None)
        for image in product_service.get_layout_images():
            self.layout_image_combo.addItem(image["name"], image["filename"])
        self.layout_image_combo.currentIndexChanged.connect(self._on_library_image_changed)
        right.addWidget(self.layout_image_combo)
        hint = QLabel("ارفع الصور من الإعدادات ← الفاتورة ← صور layout" if self.language == "ar" else "Upload images in Settings → Invoice → layout images")
        hint.setWordWrap(True)
        right.addWidget(hint)
        img_btn_row = QHBoxLayout()
        self.remove_img_btn = QPushButton(_t("remove_img", self.language))
        self.remove_img_btn.setObjectName("DangerBtn")
        self.remove_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_img_btn.setMinimumHeight(32)
        self.remove_img_btn.setVisible(False)
        self.remove_img_btn.clicked.connect(self._on_remove_image)
        img_btn_row.addWidget(self.remove_img_btn)
        right.addLayout(img_btn_row)
        right.addStretch()
        self._image_panel = QWidget()
        self._image_panel.setLayout(right)
        body_outer.addWidget(self._image_panel, 2)

        # Footer
        footer_container = QWidget()
        footer_container.setObjectName("DialogFooterContainer")
        fc = QVBoxLayout(footer_container)
        fc.setContentsMargins(0, 0, 0, 0)
        fc.setSpacing(0)
        fsep = QFrame(); fsep.setFixedHeight(1); fsep.setObjectName("Sep")
        fc.addWidget(fsep)
        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 12, 28, 16)
        fl.setSpacing(10)
        fl.addStretch()
        cancel_btn = QPushButton(_t("btn_cancel", self.language))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(40); cancel_btn.setMinimumWidth(110)
        cancel_btn.clicked.connect(self.reject)
        fl.addWidget(cancel_btn)
        save_btn = QPushButton(_t("btn_update" if is_edit else "btn_save", self.language))
        save_btn.setObjectName("PrimaryBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setMinimumHeight(40); save_btn.setMinimumWidth(140)
        save_btn.clicked.connect(self._on_save)
        fl.addWidget(save_btn)
        fc.addWidget(footer)
        root.addWidget(footer_container, 0)

        # Fill
        if is_edit:
            p = self.product
            self.code_input.setText(p.get("name") or p.get("code", ""))
            self.pattern_input.setText(p.get("pattern") or "")
            for i in range(self.cat_combo.count()):
                if self.cat_combo.itemData(i) == p.get("category"):
                    self.cat_combo.setCurrentIndex(i); break
            for i in range(self.sup_combo.count()):
                if self.sup_combo.itemData(i) == p.get("supplier_id"):
                    self.sup_combo.setCurrentIndex(i); break
            for field, inp in [
                ("ah", self.ah_input), ("l", self.l_input),
                ("w", self.w_input), ("h", self.h_input), ("oh", self.oh_input),
                ("layout", self.layout_input), ("pallet", self.pallet_input),
            ]:
                val = p.get(field)
                if val is not None:
                    inp.setText(_fmt_num(val))
            if p.get("layout_image"):
                self._show_existing_image(p["layout_image"])
                index = self.layout_image_combo.findData(p["layout_image"])
                if index >= 0:
                    self.layout_image_combo.setCurrentIndex(index)
        else:
            if self.preselected_supplier_id:
                for i in range(self.sup_combo.count()):
                    if self.sup_combo.itemData(i) == self.preselected_supplier_id:
                        self.sup_combo.setCurrentIndex(i); break
        self.cat_combo.currentIndexChanged.connect(self._on_category_changed)
        self._on_category_changed()
        self.code_input.setFocus()

    def _on_category_changed(self):
        tires = self.cat_combo.currentData() != "Batteries"
        self.identity_label.setText(_t("field_name" if tires else "field_code", self.language))
        self._identity_form.setRowVisible(self.pattern_input, tires)
        for field in (self.ah_input, self.l_input, self.w_input, self.h_input,
                      self.oh_input, self.layout_input, self.pallet_input):
            self._specs_grid.setRowVisible(field, not tires)
        self._image_panel.setVisible(not tires)
        self._specs_label.setVisible(not tires)

    def _load_suppliers(self):
        self.sup_combo.clear()
        self.sup_combo.addItem("—", None)
        for s in supplier_service.get_all(sort="name_asc"):
            self.sup_combo.addItem(f"{s['code']} — {s['name']}", s["id"])

    def _show_existing_image(self, filename):
        path = product_service.get_image_path(filename)
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.image_box.clear()
                self.image_box.setPixmap(pix.scaled(
                    160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                self.remove_img_btn.setVisible(True)

    def _on_library_image_changed(self):
        filename = self.layout_image_combo.currentData()
        self.image_box.clear()
        if filename:
            self._show_existing_image(filename)
        else:
            self.image_box.setText(_t("no_img", self.language))
        self.remove_img_btn.setVisible(bool(filename))

    def _on_remove_image(self):
        self.layout_image_combo.setCurrentIndex(0)
        self._temp_image_path = None
        self._image_removed = True
        self.image_box.clear()
        self.image_box.setText(_t("no_img", self.language))
        self.remove_img_btn.setVisible(False)

    def _on_save(self):
        code = self.code_input.text().strip()
        name = code
        cat = self.cat_combo.currentData()
        sup_id = self.sup_combo.currentData()
        if not code:
            QMessageBox.warning(self, _t("err_title", self.language), (_t("err_code_req", self.language) if cat == "Batteries" else "اسم الإطار مطلوب." if self.language == "ar" else "Tire name is required."))
            return
        if cat != "Batteries" and not self.pattern_input.text().strip():
            QMessageBox.warning(self, _t("err_title", self.language), _t("err_pattern_req", self.language))
            return
        if sup_id is None:
            QMessageBox.warning(self, _t("err_title", self.language), _t("err_supplier", self.language))
            return

        def to_num(text, is_int=False):
            text = text.strip()
            if not text:
                return None
            try:
                return int(text) if is_int else float(text)
            except ValueError:
                return None

        ah = to_num(self.ah_input.text())
        l = to_num(self.l_input.text())
        w = to_num(self.w_input.text())
        h = to_num(self.h_input.text())
        oh = to_num(self.oh_input.text())
        layout = to_num(self.layout_input.text(), True)
        pallet = to_num(self.pallet_input.text(), True)

        image_filename = self.layout_image_combo.currentData() if cat == "Batteries" else None

        try:
            if self.product is None:
                product_service.create(
                    code=code, name=name, category=cat, supplier_id=sup_id,
                    ah=ah, l=l, w=w, h=h, oh=oh,
                    layout=layout, pallet=pallet, layout_image=image_filename, pattern=self.pattern_input.text().strip())
            else:
                product_service.update(
                    self.product["id"], code=code, name=name, category=cat,
                    supplier_id=sup_id, ah=ah, l=l, w=w, h=h, oh=oh,
                    layout=layout, pallet=pallet, layout_image=image_filename, pattern=self.pattern_input.text().strip())
            self.accept()
        except ProductError as e:
            QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QWidget#DialogBody { background-color: #0A1220; }
            QWidget#DialogFooter, QWidget#DialogFooterContainer { background-color: #0A1220; }
            QLabel#DialogTitle { color: #FFFFFF; font-size: 20px; font-weight: 700; background: transparent; }
            QLabel#DialogSub { color: rgba(148,163,184,0.9); font-size: 12px; background: transparent; }
            QLabel#SectionLabel { color: #60A5FA; font-size: 13px; font-weight: 600; background: transparent; padding-top: 4px; }
            QLabel#ImgHint { color: rgba(148,163,184,0.7); font-size: 11px; background: transparent; }
            QLabel#ImageBox { background-color: rgba(15, 29, 53, 0.85); border: 2px dashed rgba(37, 99, 235, 0.4); border-radius: 12px; color: rgba(148,163,184,0.7); font-size: 13px; }
            QFrame#Sep { background-color: rgba(37, 99, 235, 0.25); border: none; }
            QLabel { color: rgba(203, 213, 225, 0.9); font-size: 13px; background: transparent; }
            QLineEdit { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 7px 11px; font-size: 13px; min-height: 20px; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QComboBox { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 7px 11px; font-size: 13px; min-height: 20px; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView { background-color: rgba(15, 29, 53, 0.98); color: #FFFFFF; selection-background-color: #2563EB; border: 1px solid rgba(37, 99, 235, 0.5); border-radius: 8px; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: transparent; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(255,255,255,0.06); }
            QPushButton#DangerBtn { background-color: rgba(220, 38, 38, 0.15); color: #F87171; border: 1px solid rgba(220, 38, 38, 0.4); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#DangerBtn:hover { background-color: rgba(220, 38, 38, 0.3); color: #FFFFFF; }
            QPushButton#AutoBtn { background-color: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 8px; padding: 7px 12px; font-size: 12px; font-weight: 500; }
            QPushButton#AutoBtn:hover { background-color: rgba(37, 99, 235, 0.3); }
            QScrollArea { background-color: #0A1220; border: none; }
            QScrollArea > QWidget > QWidget { background-color: #0A1220; }
            QScrollBar:vertical { background: transparent; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 4px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)


# ============================================================
# نافذة التفاصيل
# ============================================================
class ProductDetailsDialog(QDialog):
    def __init__(self, parent=None, language="en", theme="dark", product=None):
        super().__init__(parent)
        self.language = language
        self.palette_data = get_palette(theme)
        self.product = product
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        p = self.product
        self.setWindowTitle(_t("details_title", self.language))
        self.setMinimumWidth(620)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout(); header.setSpacing(16)
        img_box = QLabel()
        img_box.setFixedSize(120, 120)
        img_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_widget_stylesheet(img_box, "background-color: rgba(15, 29, 53, 0.85); border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 12px; color: rgba(148,163,184,0.6); font-size: 12px;")
        if p.get("layout_image"):
            path = product_service.get_image_path(p["layout_image"])
            if path:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    img_box.setPixmap(pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    img_box.setText("—")
            else:
                img_box.setText("—")
        else:
            img_box.setText("—")
        img_box.setVisible(p.get("category") == "Batteries")
        header.addWidget(img_box)

        info_col = QVBoxLayout(); info_col.setSpacing(4)
        name_lbl = QLabel(p["name"]); name_lbl.setObjectName("DialogTitle")
        info_col.addWidget(name_lbl)
        code_lbl = QLabel(_category_label(p.get("category", ""), self.language))
        code_lbl.setObjectName("DialogSub")
        info_col.addWidget(code_lbl)
        sup_lbl = QLabel(f"🏢  {p.get('supplier_name', '—')}")
        sup_lbl.setObjectName("DialogSub")
        info_col.addWidget(sup_lbl)
        info_col.addStretch()
        header.addLayout(info_col, 1)
        layout.addLayout(header)

        sep = QFrame(); sep.setFixedHeight(1); sep.setObjectName("Sep")
        layout.addWidget(sep)

        specs_label = QLabel(_t("spec_section", self.language))
        specs_label.setObjectName("SectionLabel")
        layout.addWidget(specs_label)

        grid = QHBoxLayout(); grid.setSpacing(10)
        values = [
            ("AH", p.get("ah")), ("L", p.get("l")), ("W", p.get("w")),
            ("H", p.get("h")), ("OH", p.get("oh")),
            ("layout", p.get("layout")), ("Pallet", p.get("pallet")),
        ] if p.get("category") == "Batteries" else [
            ("النقشة" if self.language == "ar" else "Pattern", p.get("pattern") or "—")]
        for label, value in values:
            box = QFrame(); box.setObjectName("StatBox")
            bl = QVBoxLayout(box); bl.setContentsMargins(10, 8, 10, 8); bl.setSpacing(2)
            lbl = QLabel(label); lbl.setObjectName("StatLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); bl.addWidget(lbl)
            val = QLabel(str(value) if p.get("category") != "Batteries" else _fmt_num(value)); val.setObjectName("StatValue")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter); bl.addWidget(val)
            grid.addWidget(box, 1)
        layout.addLayout(grid)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        close_btn = QPushButton(_t("btn_close", self.language))
        close_btn.setObjectName("PrimaryBtn")
        close_btn.setMinimumHeight(40); close_btn.setMinimumWidth(120)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QDialog { background-color: #0A1220; }
            QLabel#DialogTitle { color: #FFFFFF; font-size: 22px; font-weight: 700; background: transparent; }
            QLabel#DialogSub { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#SectionLabel { color: #60A5FA; font-size: 14px; font-weight: 600; background: transparent; }
            QFrame#Sep { background-color: rgba(37, 99, 235, 0.25); border: none; }
            QFrame#StatBox { background-color: rgba(15, 29, 53, 0.7); border: 1px solid rgba(37, 99, 235, 0.25); border-radius: 8px; }
            QLabel#StatLabel { color: rgba(148,163,184,0.85); font-size: 11px; background: transparent; }
            QLabel#StatValue { color: #FFFFFF; font-size: 15px; font-weight: 700; background: transparent; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
        """)


# ============================================================
# الصفحة الرئيسية
# ============================================================
class ProductsPage(QWidget):

    def __init__(self, theme="dark", language="en"):
        super().__init__()
        self.theme = theme
        self.language = language
        self.palette_data = get_palette(theme)
        self.column_widths = self._load_column_widths()
        self._build_ui()
        self._apply_style()
        self._reload_texts()
        self.refresh()

    def _load_column_widths(self):
        try:
            raw = settings.get("products_column_widths", "")
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return {k: int(v) for k, v in data.items() if k in PRODUCT_COL_KEYS}
        except Exception:
            pass
        return dict(PRODUCT_DEFAULT_WIDTHS)

    def _save_column_widths(self):
        try:
            settings.set("products_column_widths", json.dumps(self.column_widths))
        except Exception:
            pass

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Header
        header_card = QFrame(); header_card.setObjectName("HeaderCard")
        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(24, 18, 24, 18)

        text_col = QVBoxLayout(); text_col.setSpacing(4)
        self.title = QLabel(""); self.title.setObjectName("PageTitle")
        text_col.addWidget(self.title)
        self.subtitle = QLabel(""); self.subtitle.setObjectName("PageSub")
        text_col.addWidget(self.subtitle)
        hl.addLayout(text_col)
        hl.addStretch()

        self.export_btn = QPushButton("")
        self.export_btn.setObjectName("SecondaryBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setMinimumHeight(42)
        self.export_btn.setIcon(make_icon("file_edit", color=(self.palette_data["primary"] if self.theme == "light" else "#FFFFFF"), size=18))
        self.export_btn.setIconSize(QSize(18, 18))
        self.export_btn.clicked.connect(self._on_export)
        hl.addWidget(self.export_btn)

        self.import_btn = QPushButton("")
        self.import_btn.setObjectName("SecondaryBtn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setMinimumHeight(42)
        self.import_btn.setIcon(make_icon("archive", color=(self.palette_data["primary"] if self.theme == "light" else "#FFFFFF"), size=18))
        self.import_btn.setIconSize(QSize(18, 18))
        self.import_btn.clicked.connect(self._on_import)
        hl.addWidget(self.import_btn)

        self.new_btn = QPushButton("")
        self.new_btn.setObjectName("PrimaryBtn")
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setMinimumHeight(42)
        self.new_btn.setIcon(make_icon("products", color="#FFFFFF", size=18))
        self.new_btn.setIconSize(QSize(18, 18))
        self.new_btn.clicked.connect(self._on_new)
        hl.addWidget(self.new_btn)
        layout.addWidget(header_card)

        # Toolbar
        toolbar = QHBoxLayout(); toolbar.setSpacing(10)
        self.search_input = QLineEdit(); self.search_input.setMinimumHeight(40)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input, 2)

        self.cat_combo = QComboBox(); self.cat_combo.setMinimumHeight(40)
        self.cat_combo.setMinimumWidth(160)
        self.cat_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.cat_combo, 1)

        self.sup_combo = QComboBox(); self.sup_combo.setMinimumHeight(40)
        self.sup_combo.setMinimumWidth(180)
        self.sup_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.sup_combo, 1)

        self.sort_combo = QComboBox(); self.sort_combo.setMinimumHeight(40)
        self.sort_combo.setMinimumWidth(150)
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.sort_combo)

        self.refresh_btn = QPushButton("")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setIcon(make_icon("reports", color=(self.palette_data["primary"] if self.theme == "light" else "#FFFFFF"), size=16))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)
        layout.addLayout(toolbar)

        self.counter = QLabel(""); self.counter.setObjectName("CounterLabel")
        layout.addWidget(self.counter)

        self.table = QTableWidget()
        self.table.setColumnCount(len(PRODUCT_COLUMNS))
        self.table.setRowCount(0)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        layout.addWidget(self.table, 1)

        # Empty
        self.empty_box = QFrame(); self.empty_box.setObjectName("EmptyBox")
        el = QVBoxLayout(self.empty_box)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter); el.setSpacing(10)
        empty_icon = QLabel()
        empty_icon.setPixmap(make_icon("products", color="#2563EB", size=72).pixmap(72, 72))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(empty_icon)
        self.empty_title = QLabel(""); self.empty_title.setObjectName("EmptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(self.empty_title)
        self.empty_sub = QLabel(""); self.empty_sub.setObjectName("EmptySub")
        self.empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(self.empty_sub)
        layout.addWidget(self.empty_box, 1)
        self.empty_box.setVisible(False)

    def _on_column_resized(self, index, old_size, new_size):
        key = PRODUCT_COL_KEYS[index]
        if key in ("num", "actions"):
            return
        self.column_widths[key] = new_size
        self._save_column_widths()

    def _reload_texts(self):
        lang = self.language
        self.title.setText(_t("title", lang))
        self.subtitle.setText(_t("subtitle", lang))
        self.export_btn.setText(_t("btn_export", lang))
        self.import_btn.setText(_t("btn_import", lang))
        self.new_btn.setText(_t("btn_new", lang))
        self.refresh_btn.setText(_t("btn_refresh", lang))
        self.search_input.setPlaceholderText(_t("search_ph", lang))

        current_cat = self.cat_combo.currentData() if self.cat_combo.count() else ""
        self.cat_combo.blockSignals(True); self.cat_combo.clear()
        self.cat_combo.addItem(_t("filter_cat", lang), "")
        for cat in CATEGORIES:
            self.cat_combo.addItem(_category_label(cat, lang), cat)
        for i in range(self.cat_combo.count()):
            if self.cat_combo.itemData(i) == current_cat:
                self.cat_combo.setCurrentIndex(i); break
        self.cat_combo.blockSignals(False)

        self._reload_suppliers()

        current_sort = self.sort_combo.currentData() if self.sort_combo.count() else "name_asc"
        self.sort_combo.blockSignals(True); self.sort_combo.clear()
        for key in ["name_asc", "name_desc", "newest", "supplier"]:
            self.sort_combo.addItem(_t(f"sort_{key}", lang), key)
        for i in range(self.sort_combo.count()):
            if self.sort_combo.itemData(i) == current_sort:
                self.sort_combo.setCurrentIndex(i); break
        self.sort_combo.blockSignals(False)

        # Header
        headers = [c[2] if lang == "ar" else c[1] for c in PRODUCT_COLUMNS]
        self.table.setHorizontalHeaderLabels(headers)

        h = self.table.horizontalHeader()
        for i, (key, _en, _ar, _w) in enumerate(PRODUCT_COLUMNS):
            if key in ("num", "actions"):
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(i, self.column_widths.get(key, _w))
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(i, self.column_widths.get(key, _w))

        self.empty_title.setText(_t("no_data", lang))
        self.empty_sub.setText(_t("no_data_sub", lang))

    def _reload_suppliers(self):
        current = self.sup_combo.currentData() if self.sup_combo.count() else None
        self.sup_combo.blockSignals(True); self.sup_combo.clear()
        self.sup_combo.addItem(_t("filter_sup", self.language), None)
        for s in supplier_service.get_all(sort="name_asc"):
            self.sup_combo.addItem(s["name"], s["id"])
        for i in range(self.sup_combo.count()):
            if self.sup_combo.itemData(i) == current:
                self.sup_combo.setCurrentIndex(i); break
        self.sup_combo.blockSignals(False)

    def _on_search_changed(self):
        self.refresh()

    def refresh(self):
        search = self.search_input.text().strip()
        category = self.cat_combo.currentData() or ""
        sup_id = self.sup_combo.currentData()
        sort = self.sort_combo.currentData() or "name_asc"

        tires_only = category in CATEGORIES[1:]
        for key in ("ah", "l", "w", "h", "oh", "layout", "image"):
            self.table.setColumnHidden(PRODUCT_COL_KEYS.index(key), tires_only)
        self.table.setColumnHidden(PRODUCT_COL_KEYS.index("pattern"), category == "Batteries")
        rows = product_service.get_all(search=search, category=category,
                                       supplier_id=sup_id, sort=sort)
        self.table.setRowCount(len(rows))
        self.counter.setText(_t("count", self.language, n=len(rows)))

        if not rows:
            self.table.setVisible(False)
            self.empty_box.setVisible(True)
            if search:
                self.empty_title.setText(_t("no_results", self.language))
                self.empty_sub.setText(_t("no_results_sub", self.language))
            else:
                self.empty_title.setText(_t("no_data", self.language))
                self.empty_sub.setText(_t("no_data_sub", self.language))
            return
        else:
            self.table.setVisible(True)
            self.empty_box.setVisible(False)

        for i, p in enumerate(rows):
            self._fill_row(i, p)

    def _fill_row(self, row_idx, p):
        # #
        item = QTableWidgetItem(str(row_idx + 1))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, PRODUCT_COL_KEYS.index("num"), item)

        # Code
        code_item = QTableWidgetItem(p["code"])
        code_item.setData(Qt.ItemDataRole.UserRole, p["id"])
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, PRODUCT_COL_KEYS.index("code"), code_item)

        self.table.setItem(row_idx, PRODUCT_COL_KEYS.index("pattern"), QTableWidgetItem(p.get("pattern") or "—"))

        # AH, L, W, H, OH, Layout
        for key in ("ah", "l", "w", "h", "oh", "layout"):
            it = QTableWidgetItem(_fmt_num(p.get(key)))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, PRODUCT_COL_KEYS.index(key), it)

        # Image
        img_widget = QWidget()
        il = QHBoxLayout(img_widget)
        il.setContentsMargins(0, 0, 0, 0)
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lbl = QLabel()
        img_lbl.setFixedSize(44, 44)
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_widget_stylesheet(img_lbl, "background-color: rgba(15, 29, 53, 0.7); border: 1px solid rgba(37, 99, 235, 0.25); border-radius: 8px; color: rgba(148,163,184,0.5); font-size: 18px;")
        if p.get("layout_image"):
            path = product_service.get_image_path(p["layout_image"])
            if path:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    img_lbl.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
                else:
                    img_lbl.setText("📦")
            else:
                img_lbl.setText("📦")
        else:
            img_lbl.setText("📦")
        il.addWidget(img_lbl)
        self.table.setCellWidget(row_idx, PRODUCT_COL_KEYS.index("image"), img_widget)

        # Category
        cat_item = QTableWidgetItem(_category_label(p.get("category", ""), self.language))
        cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, PRODUCT_COL_KEYS.index("category"), cat_item)

        # Supplier
        self.table.setItem(row_idx, PRODUCT_COL_KEYS.index("supplier"),
                           QTableWidgetItem(p.get("supplier_name") or "—"))

        # Actions
        self.table.setCellWidget(row_idx, PRODUCT_COL_KEYS.index("actions"),
                                 self._make_actions_widget(p))

    def _make_actions_widget(self, p):
        w = QWidget(); w.setMinimumWidth(120)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 6, 4, 6); layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        view_btn = QPushButton("👁"); view_btn.setObjectName("IconBtn")
        view_btn.setToolTip(_t("details_title", self.language))
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setFixedSize(34, 34)
        view_btn.clicked.connect(lambda: self._on_view(p))
        layout.addWidget(view_btn)

        edit_btn = QPushButton("✏"); edit_btn.setObjectName("IconBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedSize(34, 34)
        edit_btn.clicked.connect(lambda: self._on_edit(p))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑"); del_btn.setObjectName("IconBtnDanger")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setFixedSize(34, 34)
        del_btn.clicked.connect(lambda: self._on_delete(p))
        layout.addWidget(del_btn)
        return w

    def _on_new(self):
        if supplier_service.count() == 0:
            QMessageBox.information(self, _t("err_title", self.language),
                "Please add a supplier first." if self.language != "ar"
                else "الرجاء إضافة مورد أولًا.")
            return
        dlg = ProductDialog(self, self.language, self.theme)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_import(self):
        dialog = ImportProductsDialog(self, self.language, self.theme)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.search_input.blockSignals(True)
            self.cat_combo.blockSignals(True)
            self.sup_combo.blockSignals(True)
            self.search_input.clear()
            self.cat_combo.setCurrentIndex(0)
            self.sup_combo.setCurrentIndex(0)
            self.search_input.blockSignals(False)
            self.cat_combo.blockSignals(False)
            self.sup_combo.blockSignals(False)
            self.refresh()

    def _on_export(self):
        products = product_service.get_all(
            search=self.search_input.text().strip(),
            category=self.cat_combo.currentData() or "",
            supplier_id=self.sup_combo.currentData(),
            sort=self.sort_combo.currentData() or "name_asc",
        )
        if not products:
            QMessageBox.information(
                self,
                _t("title", self.language),
                "No products match the current filters."
                if self.language != "ar" else
                "لا توجد أصناف مطابقة للفلاتر الحالية.",
            )
            return

        default_name = f"products_{date.today().isoformat()}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            _t("btn_export", self.language),
            default_name,
            "Excel Workbook (*.xlsx)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"

        try:
            export_service.export_products_excel(products, file_path, self.language)
            QMessageBox.information(
                self,
                _t("btn_export", self.language),
                f"تم تصدير {len(products)} صنف إلى:\n{file_path}"
                if self.language == "ar" else
                f"Exported {len(products)} product(s) to:\n{file_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                _t("err_title", self.language),
                f"تعذر تصدير الأصناف: {exc}"
                if self.language == "ar" else
                f"Could not export products: {exc}",
            )

    def _on_edit(self, p):
        dlg = ProductDialog(self, self.language, self.theme, product=p)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_view(self, p):
        dlg = ProductDetailsDialog(self, self.language, self.theme, product=p)
        dlg.exec()

    def _on_delete(self, p):
        reply = QMessageBox.question(self, _t("confirm_delete_t", self.language),
            _t("confirm_delete_m", self.language, name=p["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                product_service.delete(p["id"]); self.refresh()
            except ProductError as e:
                QMessageBox.warning(self, _t("err_title", self.language), str(e))

    def _on_row_double_clicked(self, item):
        row = item.row()
        code_item = self.table.item(row, PRODUCT_COL_KEYS.index("code"))
        if not code_item: return
        pid = code_item.data(Qt.ItemDataRole.UserRole)
        p = product_service.get_by_id(pid)
        if p:
            self._on_view(p)

    def reload_language(self, language):
        self.language = language
        self._reload_texts()
        self.refresh()

    def _apply_style(self):
        set_widget_stylesheet(self, """
            QWidget { background-color: #000000; }
            QFrame#HeaderCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(37, 99, 235, 0.18), stop:1 rgba(37, 99, 235, 0.02)); border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 14px; }
            QLabel#PageTitle { color: #FFFFFF; font-size: 22px; font-weight: 700; background: transparent; }
            QLabel#PageSub { color: rgba(148,163,184,0.9); font-size: 13px; background: transparent; }
            QLabel#CounterLabel { color: rgba(148,163,184,0.85); font-size: 13px; background: transparent; }
            QPushButton#PrimaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; padding: 8px 18px; }
            QPushButton#PrimaryBtn:hover { background-color: #3B82F6; }
            QPushButton#SecondaryBtn { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; font-size: 13px; font-weight: 500; padding: 8px 14px; }
            QPushButton#SecondaryBtn:hover { background-color: rgba(37, 99, 235, 0.15); border: 1px solid rgba(37, 99, 235, 0.5); }
            QLineEdit { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 8px 14px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #2563EB; }
            QComboBox { background-color: rgba(15, 29, 53, 0.85); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 8px; padding: 8px 14px; font-size: 13px; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView { background-color: rgba(15, 29, 53, 0.98); color: #FFFFFF; selection-background-color: #2563EB; border: 1px solid rgba(37, 99, 235, 0.5); border-radius: 8px; }
            QTableWidget { background-color: rgba(15, 29, 53, 0.5); color: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 12px; gridline-color: transparent; outline: none; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid rgba(37, 99, 235, 0.12); }
            QTableWidget::item:selected { background-color: rgba(37, 99, 235, 0.25); }
            QHeaderView::section { background-color: rgba(10, 22, 40, 0.9); color: rgba(148,163,184,0.9); border: none; border-bottom: 1px solid rgba(37, 99, 235, 0.3); padding: 10px 8px; font-weight: 600; font-size: 12px; }
            QPushButton#IconBtn { background-color: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid rgba(37, 99, 235, 0.4); border-radius: 8px; font-size: 15px; padding: 0; }
            QPushButton#IconBtn:hover { background-color: rgba(37, 99, 235, 0.35); color: #FFFFFF; border: 1px solid rgba(59, 130, 246, 0.7); }
            QPushButton#IconBtnDanger { background-color: rgba(220, 38, 38, 0.15); color: #F87171; border: 1px solid rgba(220, 38, 38, 0.4); border-radius: 8px; font-size: 15px; padding: 0; }
            QPushButton#IconBtnDanger:hover { background-color: rgba(220, 38, 38, 0.35); color: #FFFFFF; border: 1px solid rgba(239, 68, 68, 0.7); }
            QFrame#EmptyBox { background-color: rgba(15, 29, 53, 0.4); border: 1px dashed rgba(37, 99, 235, 0.3); border-radius: 12px; }
            QLabel#EmptyTitle { color: #FFFFFF; font-size: 20px; font-weight: 600; background: transparent; }
            QLabel#EmptySub { color: rgba(148,163,184,0.85); font-size: 14px; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: rgba(37, 99, 235, 0.4); border-radius: 5px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)