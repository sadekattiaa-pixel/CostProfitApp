"""
خدمة إدارة الأصناف (CRUD).
"""
from pathlib import Path
import unicodedata
import hashlib
import json
import uuid

from app.config import CATEGORIES
from app.db import db
from app.paths import get_products_images_dir, get_images_dir


class ProductError(Exception):
    pass


class ProductService:

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = unicodedata.normalize("NFKC", name)
        return " ".join(normalized.split()).casefold()

    @staticmethod
    def _ensure_unique_name(name: str, exclude_id: int | None = None) -> None:
        normalized_name = ProductService._normalize_name(name)
        for product in db.query_all("SELECT id, code AS name FROM products WHERE category = 'Batteries'"):
            if product["id"] == exclude_id:
                continue
            if ProductService._normalize_name(product["name"] or "") == normalized_name:
                raise ProductError(f"Product code '{name}' already exists.")

    # --------------------------------------------------------
    # قراءة
    # --------------------------------------------------------
    def get_all(
        self,
        search: str = "",
        category: str = "",
        supplier_id: int | None = None,
        sort: str = "name_asc",
    ) -> list[dict]:
        order_map = {
            "name_asc":   "p.name COLLATE NOCASE ASC",
            "name_desc":  "p.name COLLATE NOCASE DESC",
            "newest":     "p.created_at DESC",
            "oldest":     "p.created_at ASC",
            "code":       "p.name COLLATE NOCASE ASC",
            "supplier":   "s.name COLLATE NOCASE ASC",
        }
        order_by = order_map.get(sort, "p.name COLLATE NOCASE ASC")

        conditions = []
        params: list = []

        if search.strip():
            like = f"%{search.strip()}%"
            conditions.append(
                "(p.name LIKE ? OR p.pattern LIKE ? OR s.name LIKE ?)"
            )
            params += [like, like, like]

        if category:
            conditions.append("p.category = ?")
            params.append(category)

        if supplier_id:
            conditions.append("p.supplier_id = ?")
            params.append(supplier_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT
                p.id, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS code, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS name, p.category, p.pattern,
                p.ah, p.l, p.w, p.h, p.oh,
                p.layout, p.layout_image, p.pallet,
                p.supplier_id,
                s.name AS supplier_name,
                p.created_at
            FROM products p
            JOIN suppliers s ON s.id = p.supplier_id
            {where}
            ORDER BY {order_by}
        """
        return db.query_all(sql, tuple(params))

    def get_by_id(self, product_id: int) -> dict | None:
        return db.query_one(
            """
            SELECT
                p.id, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS code, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS name, p.category, p.pattern,
                p.ah, p.l, p.w, p.h, p.oh,
                p.layout, p.layout_image, p.pallet,
                p.supplier_id,
                s.name AS supplier_name,
                p.created_at
            FROM products p
            JOIN suppliers s ON s.id = p.supplier_id
            WHERE p.id = ?
            """,
            (product_id,),
        )

    def count(self) -> int:
        return db.query_one("SELECT COUNT(*) AS c FROM products")["c"]

    def get_last_purchase_price(self, product_id: int) -> float:
        row = db.query_one(
            """
            SELECT ii.purchase_usd
            FROM invoice_items ii
            JOIN invoices i ON i.id = ii.invoice_id
            WHERE ii.product_id = ? AND i.status = 'archived'
            ORDER BY i.invoice_date DESC, i.archived_at DESC, ii.id DESC
            LIMIT 1
            """,
            (product_id,),
        )
        return float(row["purchase_usd"]) if row else 0.0

    # --------------------------------------------------------
    # كتابة
    # --------------------------------------------------------
    def create(
        self,
        code: str, name: str, category: str, supplier_id: int,
        ah: float | None = None, l: float | None = None,
        w: float | None = None, h: float | None = None,
        oh: float | None = None, layout: int | None = None,
        pallet: int | None = None, layout_image: str | None = None, pattern: str = "",
    ) -> int:
        code = (code or "").strip()
        name = code if category == "Batteries" else (name or code).strip()
        pattern = (pattern or "").strip()
        if category not in CATEGORIES:
            raise ProductError(f"Invalid category: {category}")
        if category == "Batteries":
            if not code:
                raise ProductError("كود الصنف مطلوب.")
            pattern = ""
            self._ensure_unique_name(name)
        else:
            if not name:
                raise ProductError("اسم الإطار مطلوب.")
            if not pattern:
                raise ProductError("نقشة الإطار مطلوبة.")
            identity = json.dumps([category, self._normalize_name(name), self._normalize_name(pattern), supplier_id])
            code = "TIRE-" + hashlib.sha256(identity.encode()).hexdigest()
            ah = l = w = h = oh = layout = pallet = layout_image = None
        exists = db.query_one("SELECT id FROM products WHERE code = ?", (code,))
        if exists:
            raise ProductError("الصنف موجود مسبقًا: تحقق من الاسم والنقشة والمورد." if category != "Batteries" else f"Product code '{code}' already exists.")
        if not db.query_one("SELECT id FROM suppliers WHERE id = ?", (supplier_id,)):
            raise ProductError("Selected supplier does not exist.")
        db.execute(
            """
            INSERT INTO products (
                code, name, category, supplier_id, pattern,
                ah, l, w, h, oh, layout, pallet, layout_image
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (code, name, category, supplier_id, pattern,
             ah, l, w, h, oh, layout, pallet, layout_image),
        )
        db._conn.commit()
        return db.query_one("SELECT last_insert_rowid() AS id")["id"]

    def update(
        self,
        product_id: int,
        code: str, name: str, category: str, supplier_id: int,
        ah: float | None = None, l: float | None = None,
        w: float | None = None, h: float | None = None,
        oh: float | None = None, layout: int | None = None,
        pallet: int | None = None, layout_image: str | None = None, pattern: str = "",
    ) -> None:
        code = (code or "").strip()
        name = code if category == "Batteries" else (name or code).strip()
        pattern = (pattern or "").strip()
        if category not in CATEGORIES:
            raise ProductError(f"Invalid category: {category}")
        if category == "Batteries":
            if not code:
                raise ProductError("كود الصنف مطلوب.")
            pattern = ""
            self._ensure_unique_name(name, exclude_id=product_id)
        else:
            if not name:
                raise ProductError("اسم الإطار مطلوب.")
            if not pattern:
                raise ProductError("نقشة الإطار مطلوبة.")
            identity = json.dumps([category, self._normalize_name(name), self._normalize_name(pattern), supplier_id])
            code = "TIRE-" + hashlib.sha256(identity.encode()).hexdigest()
            ah = l = w = h = oh = layout = pallet = layout_image = None
        exists = db.query_one("SELECT id FROM products WHERE code = ? AND id != ?", (code, product_id))
        if exists:
            raise ProductError("الصنف موجود مسبقًا: تحقق من الاسم والنقشة والمورد." if category != "Batteries" else f"Product code '{code}' already exists.")
        if not db.query_one("SELECT id FROM suppliers WHERE id = ?", (supplier_id,)):
            raise ProductError("Selected supplier does not exist.")
        db.execute(
            """
            UPDATE products
               SET code = ?, name = ?, category = ?, supplier_id = ?, pattern = ?,
                   ah = ?, l = ?, w = ?, h = ?, oh = ?,
                   layout = ?, pallet = ?, layout_image = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (code, name, category, supplier_id, pattern,
             ah, l, w, h, oh, layout, pallet, layout_image, product_id),
        )
        db._conn.commit()

    def delete(self, product_id: int) -> None:
        # منع الحذف إذا كان مستخدمًا في فواتير
        count = db.query_one(
            "SELECT COUNT(*) AS c FROM invoice_items WHERE product_id = ?",
            (product_id,),
        )["c"]
        if count > 0:
            raise ProductError(
                f"Cannot delete: product is used in {count} invoice item(s)."
            )

        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db._conn.commit()

    # --------------------------------------------------------
    # صور المنتجات
    # --------------------------------------------------------
    def save_layout_image(self, product_code: str, source_path: str) -> str:
        """ينسخ الصورة إلى مجلد المنتجات ويُرجع اسم الملف."""
        import shutil
        from pathlib import Path as _Path

        src = _Path(source_path)
        if not src.exists():
            raise ProductError("Image file does not exist.")

        ext = src.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            raise ProductError("Only JPG and PNG images are supported.")

        size_mb = src.stat().st_size / (1024 * 1024)
        if size_mb > 1.5:
            raise ProductError(f"Image is too large ({size_mb:.1f} MB). Max 1.5 MB.")

        target_dir = get_products_images_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = hashlib.sha256(str(product_code).encode()).hexdigest()[:24] + "-" + uuid.uuid4().hex + ext
        target = target_dir / filename
        shutil.copy2(src, target)
        return filename

    def get_image_path(self, filename: str) -> Path | None:
        if not filename:
            return None
        p = (get_products_images_dir() / filename).resolve()
        base = get_images_dir().resolve()
        if base not in p.parents:
            raise ProductError("Invalid image path.")
        return p if p.is_file() else None

    def get_layout_images(self):
        return db.query_all("SELECT li.*, (SELECT COUNT(*) FROM products p WHERE p.layout_image=li.filename) AS uses FROM layout_images li ORDER BY name COLLATE NOCASE")

    def add_layout_image(self, name: str, source_path: str) -> str:
        from PIL import Image as PillowImage
        source = Path(source_path)
        name = name.strip() or source.stem.strip()
        if not name:
            raise ProductError("اسم الصورة مطلوب. / Image name is required.")
        try:
            with PillowImage.open(source) as image:
                image.verify()
        except Exception as exc:
            raise ProductError("الصورة غير صالحة. / Invalid image.") from exc
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        existing = db.query_one("SELECT filename FROM layout_images WHERE checksum=?", (checksum,))
        if existing:
            return existing["filename"]
        filename = self.save_layout_image("library", str(source))
        try:
            with db.transaction():
                db.execute("INSERT INTO layout_images(filename,name,checksum) VALUES(?,?,?)", (filename,name,checksum))
        except Exception:
            self.get_image_path(filename).unlink(missing_ok=True)
            raise
        return filename

    def delete_layout_image(self, filename: str) -> None:
        with db.transaction(immediate=True):
            if db.query_one("SELECT COUNT(*) AS n FROM products WHERE layout_image=?", (filename,))["n"]:
                raise ProductError("الصورة مرتبطة بأصناف؛ ألغِ ارتباطها أولًا. / Image is in use.")
            if not db.query_one("SELECT filename FROM layout_images WHERE filename=?", (filename,)):
                raise ProductError("Image not found.")
            path = self.get_image_path(filename)
            if path:
                path.unlink()
            db.execute("DELETE FROM layout_images WHERE filename=?", (filename,))

    def reset_legacy_layout_images(self) -> None:
        from app.services.settings_service import settings
        from app.services.invoice_service import invoice_service
        from app.services.backup_service import backup_service
        if settings.get_bool("layout_library_initialized", False):
            return
        backup_service.create_backup()
        invoice_service.freeze_existing_archives()
        with db.transaction(immediate=True):
            db.execute("UPDATE products SET layout_image=NULL")
            db.execute("DELETE FROM layout_images")
        directory = get_products_images_dir().resolve()
        if directory.exists():
            for path in directory.iterdir():
                if path.is_file() and not path.is_symlink() and path.resolve().parent == directory:
                    path.unlink()
        settings.set("layout_library_initialized", True)


# Singleton
product_service = ProductService()