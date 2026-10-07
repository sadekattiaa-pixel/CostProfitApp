"""
خدمة إدارة الفواتير — CRUD كامل.
"""
from datetime import date
import json
import hashlib
import shutil
from pathlib import Path

from app.db import db
from app.services.invoice_calc import (
    calculate_invoice, InvoiceItemInput, InvoiceCalculation, CalculationError,
)
from app.services.error_logging import log_failures


class InvoiceError(Exception):
    pass


class InvoiceService:

    # --------------------------------------------------------
    # توليد رقم الفاتورة التلقائي
    # --------------------------------------------------------
    def generate_invoice_number(self) -> str:
        year = date.today().year
        from app.services.settings_service import settings
        configured_prefix = str(settings.get("invoice_prefix") or "INV-").strip() or "INV-"
        prefix = f"{configured_prefix}{year}-"
        rows = db.query_all(
            "SELECT invoice_no FROM invoices WHERE invoice_no LIKE ?",
            (f"{prefix}%",),
        )
        max_num = 0
        for r in rows:
            code = r["invoice_no"] or ""
            if code.startswith(prefix):
                try:
                    n = int(code[len(prefix):])
                    if n > max_num:
                        max_num = n
                except ValueError:
                    pass
        return f"{prefix}{max_num + 1:04d}"

    # --------------------------------------------------------
    # قراءة
    # --------------------------------------------------------
    def get_by_id(self, invoice_id: int) -> dict | None:
        inv = db.query_one(
            """
            SELECT
                i.*,
                s.name AS supplier_name,
                s.code AS supplier_code,
                s.address AS supplier_address,
                s.phone AS supplier_phone,
                s.email AS supplier_email
            FROM invoices i
            JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.id = ?
            """,
            (invoice_id,),
        )
        if not inv:
            return None

        if inv["status"] == "archived" and inv.get("archived_snapshot") and json.loads(inv["archived_snapshot"]).get("status") == "archived":
            frozen = json.loads(inv["archived_snapshot"])
            frozen.update(id=inv["id"], status=inv["status"], archived_at=inv["archived_at"])
            return frozen

        inv["items"] = db.query_all(
            """
            SELECT
                ii.*,
                CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS product_code,
                CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS product_name,
                p.pattern AS product_pattern,
                p.category AS product_category,
                p.layout_image AS product_image,
                p.ah AS product_ah,
                p.l AS product_l,
                p.w AS product_w,
                p.h AS product_h,
                p.oh AS product_oh,
                p.layout AS product_layout,
                p.pallet AS product_pallet
            FROM invoice_items ii
            JOIN products p ON p.id = ii.product_id
            WHERE ii.invoice_id = ?
            ORDER BY ii.line_no
            """,
            (invoice_id,),
        )
        inv["payments"] = db.query_all(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY line_no",
            (invoice_id,),
        )
        inv["discounts"] = db.query_all(
            "SELECT * FROM invoice_discounts WHERE invoice_id = ? ORDER BY line_no",
            (invoice_id,),
        )
        inv["expenses"] = db.query_all(
            "SELECT * FROM invoice_expenses WHERE invoice_id = ? ORDER BY line_no",
            (invoice_id,),
        )
        if inv.get("archived_snapshot"):
            copied = json.loads(inv["archived_snapshot"])
            if copied.get("supplier_id") == inv["supplier_id"]:
                for key in ("name", "code", "address", "phone", "email"):
                    inv["supplier_" + key] = copied.get("supplier_" + key, inv.get("supplier_" + key))
            if "_company_snapshot" in copied:
                inv["_company_snapshot"] = copied["_company_snapshot"]
            for item in inv["items"]:
                original = next((old for old in copied.get("items", []) if old.get("line_no") == item["line_no"] and old.get("product_id") == item["product_id"]), None)
                if original:
                    item.update({key: value for key, value in original.items() if key.startswith("product_")})
        if inv["status"] == "draft":
            from app.services.settings_service import settings
            inv["notes"] = settings.get("invoice_notes") or ""
            inv["notes2"] = settings.get("invoice_notes2") or ""
        return inv

    def get_all(
        self,
        status: str = "archived",
        search: str = "",
        supplier_id: int | None = None,
        date_from: str = "",
        date_to: str = "",
        sort: str = "newest",
    ) -> list[dict]:
        order_map = {
            "newest":   "i.created_at DESC",
            "oldest":   "i.created_at ASC",
            "date_new": "i.invoice_date DESC",
            "date_old": "i.invoice_date ASC",
            "profit_high": "i.total_profit DESC",
            "profit_low":  "i.total_profit ASC",
            "usd_high":    "i.total_usd DESC",
        }
        order_by = order_map.get(sort, "i.created_at DESC")

        conditions = ["i.status = ?"]
        params: list = [status]

        if search.strip():
            like = f"%{search.strip()}%"
            conditions.append(
                "(i.invoice_no LIKE ? OR i.supplier_invoice_no LIKE ? OR COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) LIKE ?)"
            )
            params += [like, like, like]

        if supplier_id:
            conditions.append("i.supplier_id = ?")
            params.append(supplier_id)

        if date_from:
            conditions.append("i.invoice_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("i.invoice_date <= ?")
            params.append(date_to)

        where = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT
                i.id, i.invoice_no, i.supplier_invoice_no, i.invoice_date,
                i.status, i.total_payments, i.total_usd, i.total_profit,
                i.net_cost, i.profit_margin,
                i.created_at, i.archived_at,
                COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) AS supplier_name,
                COALESCE(json_extract(i.archived_snapshot, '$.supplier_code'), s.code) AS supplier_code,
                (SELECT COALESCE(SUM(quantity), 0)
                   FROM invoice_items
                  WHERE invoice_id = i.id) AS total_qty
            FROM invoices i
            JOIN suppliers s ON s.id = i.supplier_id
            {where}
            ORDER BY {order_by}
        """
        return db.query_all(sql, tuple(params))

    def count_by_status(self, status: str) -> int:
        return db.query_one(
            "SELECT COUNT(*) AS c FROM invoices WHERE status = ?",
            (status,),
        )["c"]

    # --------------------------------------------------------
    # الحفظ
    # --------------------------------------------------------
    @log_failures("save an invoice draft")
    def save_draft(
        self,
        invoice_id: int | None,
        supplier_id: int,
        supplier_invoice_no: str,
        invoice_date: str,
        items: list[dict],
        payments: list[dict],
        discounts: list[dict],
        expenses: list[dict],
        display_fields: str | None = None,
        notes: str = "",
        notes2: str = "",
    ) -> int:
        with db.transaction(immediate=True):
            return self._save_draft_uncommitted(
                invoice_id, supplier_id, supplier_invoice_no, invoice_date,
                items, payments, discounts, expenses, display_fields, notes, notes2,
            )

    def _save_draft_uncommitted(
        self,
        invoice_id: int | None,
        supplier_id: int,
        supplier_invoice_no: str,
        invoice_date: str,
        items: list[dict],
        payments: list[dict],
        discounts: list[dict],
        expenses: list[dict],
        display_fields: str | None = None,
        notes: str = "",
        notes2: str = "",
    ) -> int:
        from app.services.settings_service import settings
        notes = settings.get("invoice_notes") or ""
        notes2 = settings.get("invoice_notes2") or ""
        if not supplier_id:
            raise InvoiceError("Supplier is required.")
        if not items:
            raise InvoiceError("At least one product is required.")

        previous = db.query_one("SELECT archived_snapshot FROM invoices WHERE id=?", (invoice_id,)) if invoice_id else None
        copied = json.loads(previous["archived_snapshot"]) if previous and previous.get("archived_snapshot") else None
        calc = self._calculate(items, payments, discounts, expenses)

        if invoice_id is None:
            invoice_no = self.generate_invoice_number()
            db.execute(
                """
                INSERT INTO invoices (
                    invoice_no, supplier_invoice_no, supplier_id, invoice_date,
                    status, total_payments, total_discounts, net_payments,
                    total_expenses, net_cost, total_usd, exchange_rate,
                    total_sales, total_profit, profit_margin, display_fields
                ) VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice_no, supplier_invoice_no.strip(), supplier_id, invoice_date,
                 calc.total_payments, calc.total_discounts, calc.net_payments,
                 calc.total_expenses, calc.net_cost, calc.total_usd, calc.exchange_rate,
                 calc.total_sales, calc.total_profit, calc.profit_margin, display_fields),
            )
            invoice_id = db.query_one("SELECT last_insert_rowid() AS id")["id"]
        else:
            existing = db.query_one(
                "SELECT status FROM invoices WHERE id = ?", (invoice_id,),
            )
            if not existing:
                raise InvoiceError("Invoice not found.")
            if existing["status"] != "draft":
                raise InvoiceError("Only drafts can be edited.")

            db.execute(
                """
                UPDATE invoices SET
                    supplier_invoice_no = ?, supplier_id = ?, invoice_date = ?,
                    total_payments = ?, total_discounts = ?, net_payments = ?,
                    total_expenses = ?, net_cost = ?, total_usd = ?,
                    exchange_rate = ?, total_sales = ?, total_profit = ?,
                    profit_margin = ?, display_fields = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (supplier_invoice_no.strip(), supplier_id, invoice_date,
                 calc.total_payments, calc.total_discounts, calc.net_payments,
                 calc.total_expenses, calc.net_cost, calc.total_usd, calc.exchange_rate,
                 calc.total_sales, calc.total_profit, calc.profit_margin,
                 display_fields, invoice_id),
            )

            db.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            db.execute("DELETE FROM invoice_payments WHERE invoice_id = ?", (invoice_id,))
            db.execute("DELETE FROM invoice_discounts WHERE invoice_id = ?", (invoice_id,))
            db.execute("DELETE FROM invoice_expenses WHERE invoice_id = ?", (invoice_id,))

        for i, it in enumerate(calc.items):
            pallet = items[i].get("pallet")
            pallet = int(float(pallet)) if pallet is not None else None
            db.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id, product_id, line_no, quantity, pallet,
                    purchase_usd, purchase_dzd, sale_dzd,
                    total_usd, total_dzd, total_sale, unit_profit, total_profit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice_id, it.product_id, i + 1, it.quantity, pallet,
                 it.purchase_usd, it.purchase_dzd, it.sale_dzd,
                 it.total_usd, it.total_dzd, it.total_sale,
                 it.unit_profit, it.total_profit),
            )

        for i, p in enumerate(payments):
            db.execute(
                "INSERT INTO invoice_payments (invoice_id, label, amount, line_no) VALUES (?, ?, ?, ?)",
                (invoice_id, p.get("label", ""), float(p.get("amount", 0)), i + 1),
            )

        for i, d in enumerate(discounts):
            db.execute(
                "INSERT INTO invoice_discounts (invoice_id, label, amount, line_no) VALUES (?, ?, ?, ?)",
                (invoice_id, d.get("label", ""), float(d.get("amount", 0)), i + 1),
            )

        for i, e in enumerate(expenses):
            db.execute(
                "INSERT INTO invoice_expenses (invoice_id, label, amount, line_no) VALUES (?, ?, ?, ?)",
                (invoice_id, e.get("label", ""), float(e.get("amount", 0)), i + 1),
            )

        db.execute("UPDATE invoices SET notes = ? WHERE id = ?", (notes, invoice_id))
        db.execute("UPDATE invoices SET notes2 = ? WHERE id = ?", (notes2, invoice_id))
        if copied:
            if copied.get("supplier_id") != supplier_id:
                for key in ("name", "code", "address", "phone", "email"):
                    copied.pop("supplier_" + key, None)
                copied["supplier_id"] = supplier_id
            old_items = copied.get("items", [])
            copied["items"] = []
            for index, item in enumerate(items, 1):
                if "_product_snapshot" in item:
                    original = item["_product_snapshot"]
                else:
                    original = next((old for old in old_items if old.get("line_no") == index and old.get("product_id") == item["product_id"]), None)
                if original:
                    copied["items"].append(dict(original, line_no=index, product_id=item["product_id"]))
            db.execute("UPDATE invoices SET archived_snapshot=? WHERE id=?", (json.dumps(copied, ensure_ascii=False), invoice_id))
        return invoice_id

    # --------------------------------------------------------
    # الأرشفة
    # --------------------------------------------------------
    @log_failures("archive an invoice")
    def archive(
        self,
        invoice_id: int,
        supplier_id: int,
        supplier_invoice_no: str,
        invoice_date: str,
        items: list[dict],
        payments: list[dict],
        discounts: list[dict],
        expenses: list[dict],
        display_fields: str | None = None,
        notes: str = "",
        notes2: str = "",
    ) -> int:
        with db.transaction(immediate=True):
            invoice_id = self._save_draft_uncommitted(
                invoice_id, supplier_id, supplier_invoice_no, invoice_date,
                items, payments, discounts, expenses, display_fields, notes, notes2,
            )
            db.execute(
                "UPDATE invoices SET status = 'archived', archived_at = datetime('now') WHERE id = ?",
                (invoice_id,),
            )
            self.freeze_archive(invoice_id)
            return invoice_id

    def freeze_archive(self, invoice_id: int) -> None:
        """Store the invoice identity and immutable copies of referenced images."""
        from app.services.settings_service import settings
        from app.services.product_service import product_service
        from app.paths import get_images_dir, get_company_dir
        existing = db.query_one("SELECT status, archived_snapshot FROM invoices WHERE id = ?", (invoice_id,))
        if not existing or existing["status"] != "archived" or (existing.get("archived_snapshot") and json.loads(existing["archived_snapshot"]).get("status") == "archived"):
            return
        invoice = self.get_by_id(invoice_id)
        archive_dir = get_images_dir() / "Archive"
        def preserve(source):
            if not source or not source.is_file():
                return None
            archive_dir.mkdir(parents=True, exist_ok=True)
            filename = hashlib.sha256(source.read_bytes()).hexdigest() + source.suffix.lower()
            target = archive_dir / filename
            if not target.exists():
                shutil.copy2(source, target)
            return "../Archive/" + filename
        for item in invoice["items"]:
            item["product_image"] = preserve(product_service.get_image_path(item.get("product_image")))
            if item.get("pallet") is None:
                item["pallet"] = item.get("product_pallet")
        company = dict(invoice["_company_snapshot"]) if "_company_snapshot" in invoice else {key: settings.get(key) or "" for key in
                   ("company_name", "company_address", "company_phone", "company_email", "company_website", "company_logo")}
        logo = company["company_logo"]
        company["company_logo"] = preserve(get_company_dir() / logo) if logo else ""
        invoice["_company_snapshot"] = company
        from app.services.export_service import _current_marks
        marks = _current_marks()
        for kind in ("stamp", "signature"):
            key = "invoice_" + kind + "_image"
            if marks.get(key):marks[key] = preserve(get_images_dir() / "Marks" / marks[key]) or ""
        invoice["_marks_snapshot"] = marks
        invoice.pop("archived_snapshot", None)
        db.execute("UPDATE invoices SET archived_snapshot = ? WHERE id = ?",
                   (json.dumps(invoice, ensure_ascii=False), invoice_id))

    def freeze_existing_archives(self) -> None:
        with db.transaction(immediate=True):
            for row in db.query_all("SELECT id FROM invoices WHERE status='archived' AND archived_snapshot IS NULL"):
                self.freeze_archive(row["id"])

    # --------------------------------------------------------
    # الحذف
    # --------------------------------------------------------
    @log_failures("delete an invoice")
    def delete(self, invoice_id: int) -> None:
        db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        db._conn.commit()

    # --------------------------------------------------------
    # إحصائيات
    # --------------------------------------------------------
    def get_stats(self, status: str = "archived") -> dict:
        row = db.query_one(
            """
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(total_payments), 0) AS payments,
                COALESCE(SUM(total_usd), 0)      AS usd,
                COALESCE(SUM(total_profit), 0)   AS profit
            FROM invoices
            WHERE status = ?
            """,
            (status,),
        ) or {}
        return {
            "count": row.get("count", 0),
            "payments": row.get("payments", 0),
            "usd": row.get("usd", 0),
            "profit": row.get("profit", 0),
        }

    # --------------------------------------------------------
    # مساعدات
    # --------------------------------------------------------
    def _calculate(
        self,
        items: list[dict],
        payments: list[dict],
        discounts: list[dict],
        expenses: list[dict],
    ) -> InvoiceCalculation:
        item_inputs = []
        for it in items:
            if not it.get("product_id"):
                raise InvoiceError("All rows must have a product.")
            try:
                qty = float(it.get("quantity") or 0)
                pu = float(it.get("purchase_usd") or 0)
                sd = float(it.get("sale_dzd") or 0)
                pallet = it.get("pallet")
                if pallet is not None:
                    pallet_value = float(pallet)
                    if pallet_value < 0 or not pallet_value.is_integer():
                        raise ValueError
            except (TypeError, ValueError):
                raise InvoiceError("Invalid numeric value in items.")
            item_inputs.append(InvoiceItemInput(
                product_id=it["product_id"],
                quantity=qty,
                purchase_usd=pu,
                sale_dzd=sd,
            ))

        payment_amounts = [p.get("amount") or 0 for p in payments]
        discount_amounts = [d.get("amount") or 0 for d in discounts]
        expense_amounts = [e.get("amount") or 0 for e in expenses]

        try:
            return calculate_invoice(
                item_inputs, payment_amounts, discount_amounts, expense_amounts,
            )
        except CalculationError as e:
            raise InvoiceError(str(e))

    def calculate_preview(
        self,
        items: list[dict],
        payments: list[dict],
        discounts: list[dict],
        expenses: list[dict],
    ) -> InvoiceCalculation | None:
        try:
            return self._calculate(items, payments, discounts, expenses)
        except InvoiceError:
            return None

    # --------------------------------------------------------
    # نسخ فاتورة إلى مسودة جديدة
    # --------------------------------------------------------
    def duplicate_invoice(self, invoice_id: int,
                          invoice_date: str | None = None) -> int:
        """
        يُنشئ نسخة جديدة (مسودة) من فاتورة موجودة.
        Returns: معرّف الفاتورة الجديدة.
        """
        original = self.get_by_id(invoice_id)
        if not original:
            raise InvoiceError("Invoice not found.")

        items = []
        for it in original.get("items", []):
            if not it.get("product_id"):
                continue
            pallet = it.get("pallet")
            if pallet is None:
                pallet = it.get("product_pallet")
            items.append({
                "product_id":   it["product_id"],
                "quantity":     it.get("quantity", 0),
                "purchase_usd": it.get("purchase_usd", 0),
                "sale_dzd":     it.get("sale_dzd", 0),
                "pallet":       pallet,
            })

        if not items:
            raise InvoiceError("Original invoice has no items.")

        payments = [
            {"label": p.get("label") or "", "amount": p.get("amount", 0)}
            for p in original.get("payments", [])
        ]
        discounts = [
            {"label": d.get("label") or "", "amount": d.get("amount", 0)}
            for d in original.get("discounts", [])
        ]
        expenses = [
            {"label": e.get("label") or "", "amount": e.get("amount", 0)}
            for e in original.get("expenses", [])
        ]

        if not invoice_date:
            invoice_date = original["invoice_date"]

        with db.transaction(immediate=True):
            return self._duplicate_from_data(original, items, payments, discounts, expenses, invoice_date)

    def _duplicate_from_data(self, original, items, payments, discounts, expenses, invoice_date):
        new_id = self.save_draft(
            invoice_id=None,
            supplier_id=original["supplier_id"],
            supplier_invoice_no=original.get("supplier_invoice_no") or "",
            invoice_date=invoice_date,
            items=items,
            payments=payments,
            discounts=discounts,
            expenses=expenses,
            display_fields=original.get("display_fields"),
            notes=original.get("notes") or "",
            notes2=original.get("notes2") or "",
        )
        copied = dict(original, id=new_id, status="draft")
        copied.pop("archived_snapshot", None)
        if "_company_snapshot" not in copied:
            from app.services.settings_service import settings
            copied["_company_snapshot"] = {key: settings.get(key) or "" for key in ("company_name", "company_address", "company_phone", "company_email", "company_website", "company_logo")}
        db.execute("UPDATE invoices SET archived_snapshot=? WHERE id=?", (json.dumps(copied, ensure_ascii=False), new_id))
        return new_id


invoice_service = InvoiceService()
