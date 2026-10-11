"""
خدمة إدارة الموردين (CRUD).
"""
from app.db import db


class SupplierError(Exception):
    pass


class SupplierService:

    @staticmethod
    def resolve_reference(reference: str, suppliers: list[dict]) -> dict | None:
        key = reference.strip().casefold()
        codes = [s for s in suppliers if s["code"].strip().casefold() == key]
        matches = codes or [s for s in suppliers if s["name"].strip().casefold() == key]
        if len(matches) > 1:
            raise SupplierError("المورد غير محدد: استخدم كود المورد الفريد. / Ambiguous supplier; use its unique code.")
        return matches[0] if matches else None

    # --------------------------------------------------------
    # قراءة
    # --------------------------------------------------------
    def get_all(
        self,
        search: str = "",
        sort: str = "newest",
        limit: int | None = None,
        offset: int = 0,
        count_only: bool = False,
    ) -> list[dict] | int:
        """يُرجع كل الموردين مع إمكانية البحث والترتيب."""
        order_map = {
            "newest":     "s.created_at DESC",
            "oldest":     "s.created_at ASC",
            "name_asc":   "s.name COLLATE NOCASE ASC",
            "name_desc":  "s.name COLLATE NOCASE DESC",
            "most_products": "products_count DESC",
            "most_invoices": "invoices_count DESC",
        }
        order_by = order_map.get(sort, "s.created_at DESC")

        where = ""
        params: list = []
        if search.strip():
            like = f"%{search.strip()}%"
            where = """
                WHERE s.name LIKE ?
                   OR s.code LIKE ?
                   OR s.phone LIKE ?
                   OR s.email LIKE ?
            """
            params = [like, like, like, like]

        sql = f"""
            SELECT
                s.id, s.code, s.name, s.address, s.email, s.phone, s.created_at,
                (SELECT COUNT(*) FROM products WHERE supplier_id = s.id) AS products_count,
                (SELECT COUNT(*) FROM invoices WHERE supplier_id = s.id) AS invoices_count
            FROM suppliers s
            {where}
            ORDER BY {order_by}, s.id DESC
        """
        if count_only:
            filtered = sql.rsplit("ORDER BY", 1)[0]
            return db.query_one(f"SELECT COUNT(*) AS n FROM ({filtered})", tuple(params))["n"]
        if limit is not None:
            if limit < 1 or offset < 0:
                raise ValueError("Invalid page bounds")
            sql += " LIMIT ? OFFSET ?"
            params += [int(limit), int(offset)]
        return db.query_all(sql, tuple(params))

    def get_by_id(self, supplier_id: int) -> dict | None:
        return db.query_one(
            """
            SELECT
                s.id, s.code, s.name, s.address, s.email, s.phone, s.created_at,
                (SELECT COUNT(*) FROM products WHERE supplier_id = s.id) AS products_count,
                (SELECT COUNT(*) FROM invoices WHERE supplier_id = s.id) AS invoices_count
            FROM suppliers s
            WHERE s.id = ?
            """,
            (supplier_id,),
        )

    def get_stats(self, supplier_id: int) -> dict:
        """إحصائيات مورد واحد."""
        row = db.query_one(
            """
            SELECT
                COUNT(*) AS invoices_count,
                COALESCE(SUM(total_payments), 0) AS total_payments,
                COALESCE(SUM(total_usd), 0)      AS total_usd,
                COALESCE(SUM(total_profit), 0)   AS total_profit
            FROM invoices
            WHERE supplier_id = ? AND status = 'archived'
            """,
            (supplier_id,),
        ) or {}

        products_count = db.query_one(
            "SELECT COUNT(*) AS c FROM products WHERE supplier_id = ?",
            (supplier_id,),
        )["c"]

        return {
            "invoices_count": row.get("invoices_count", 0),
            "total_payments": row.get("total_payments", 0),
            "total_usd":      row.get("total_usd", 0),
            "total_profit":   row.get("total_profit", 0),
            "products_count": products_count,
        }

    def count(self) -> int:
        return db.query_one("SELECT COUNT(*) AS c FROM suppliers")["c"]

    # --------------------------------------------------------
    # كتابة
    # --------------------------------------------------------
    def create(self, code: str, name: str, address: str = "",
               email: str = "", phone: str = "") -> int:
        with db.transaction(immediate=True):
            code = code.strip()
            name = name.strip()

            if not code:
                raise SupplierError("Supplier code is required.")
            if not name:
                raise SupplierError("Supplier name is required.")

            # تحقق من التفرد
            exists = db.query_one("SELECT id FROM suppliers WHERE code = ?", (code,))
            if exists:
                raise SupplierError(f"Supplier code '{code}' already exists.")

            db.execute(
                """
                INSERT INTO suppliers (code, name, address, email, phone)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code, name, address.strip(), email.strip(), phone.strip()),
            )
            return db.query_one("SELECT last_insert_rowid() AS id")["id"]

    def update(self, supplier_id: int, code: str, name: str,
               address: str = "", email: str = "", phone: str = "") -> None:
        with db.transaction(immediate=True):
            code = code.strip()
            name = name.strip()

            if not code:
                raise SupplierError("Supplier code is required.")
            if not name:
                raise SupplierError("Supplier name is required.")

            exists = db.query_one(
                "SELECT id FROM suppliers WHERE code = ? AND id != ?",
                (code, supplier_id),
            )
            if exists:
                raise SupplierError(f"Supplier code '{code}' already exists.")

            db.execute(
                """
                UPDATE suppliers
                   SET code = ?, name = ?, address = ?, email = ?, phone = ?
                 WHERE id = ?
                """,
                (code, name, address.strip(), email.strip(), phone.strip(), supplier_id),
            )

    def delete(self, supplier_id: int) -> None:
        # منع الحذف إذا كان له أصناف أو فواتير
        with db.transaction(immediate=True):
            products_count = db.query_one(
                "SELECT COUNT(*) AS c FROM products WHERE supplier_id = ?",
                (supplier_id,),
            )["c"]
            invoices_count = db.query_one(
                "SELECT COUNT(*) AS c FROM invoices WHERE supplier_id = ?",
                (supplier_id,),
            )["c"]

            if products_count > 0 or invoices_count > 0:
                raise SupplierError(
                    f"Cannot delete: supplier has {products_count} products "
                    f"and {invoices_count} invoices."
                )

            db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

    # --------------------------------------------------------
    # توليد الكود التالي
    # --------------------------------------------------------
    def generate_code(self) -> str:
        """يولّد كودًا تسلسليًا مثل S-004."""
        rows = db.query_all("SELECT code FROM suppliers")
        max_num = 0
        for r in rows:
            code = r["code"] or ""
            if code.startswith("S-"):
                try:
                    n = int(code[2:])
                    if n > max_num:
                        max_num = n
                except ValueError:
                    pass
        return f"S-{max_num + 1:03d}"


# Singleton
supplier_service = SupplierService()