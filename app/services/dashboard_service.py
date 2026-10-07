"""
خدمة Dashboard: تجمع الإحصائيات من قاعدة البيانات.
"""
from datetime import date, timedelta

from app.db import db


# ============================================================
# الفترات الزمنية
# ============================================================
def _period_range(period: str) -> tuple[str, str]:
    """يُرجع (from_date, to_date) بصيغة YYYY-MM-DD."""
    today = date.today()
    to_str = today.isoformat()

    if period == "today":
        from_str = today.isoformat()
    elif period == "week":
        from_str = (today - timedelta(days=today.weekday())).isoformat()
    elif period == "month":
        from_str = today.replace(day=1).isoformat()
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        from_str = today.replace(month=q_start_month, day=1).isoformat()
    elif period == "year":
        from_str = today.replace(month=1, day=1).isoformat()
    else:  # all
        from_str = "1900-01-01"

    return from_str, to_str


# ============================================================
# الخدمة
# ============================================================
class DashboardService:

    def get_kpis(self, period: str = "year") -> dict:
        """يُرجع بطاقات KPI الخمس."""
        f, t = _period_range(period)

        row = db.query_one(
            """
            SELECT
                COUNT(*)              AS invoices_count,
                COALESCE(SUM(total_payments), 0) AS total_payments,
                COALESCE(SUM(total_usd), 0)      AS total_usd,
                COALESCE(SUM(total_profit), 0)   AS total_profit
            FROM invoices
            WHERE status = 'archived'
              AND invoice_date BETWEEN ? AND ?
            """,
            (f, t),
        ) or {}

        open_row = db.query_one(
            "SELECT COUNT(*) AS c FROM invoices WHERE status = 'draft'"
        ) or {"c": 0}

        return {
            "invoices_count": row.get("invoices_count", 0) or 0,
            "total_payments": row.get("total_payments", 0) or 0,
            "total_usd":      row.get("total_usd", 0) or 0,
            "total_profit":   row.get("total_profit", 0) or 0,
            "open_invoices":  open_row.get("c", 0) or 0,
        }

    def get_profit_trend(self, period: str = "year") -> list[dict]:
        """اتجاه الأرباح الشهري."""
        f, t = _period_range(period)
        rows = db.query_all(
            """
            SELECT
                strftime('%Y-%m', invoice_date) AS ym,
                COALESCE(SUM(total_profit), 0)  AS profit
            FROM invoices
            WHERE status = 'archived'
              AND invoice_date BETWEEN ? AND ?
            GROUP BY ym
            ORDER BY ym
            """,
            (f, t),
        )
        return [{"month": r["ym"], "profit": r["profit"]} for r in rows]

    def get_profit_by_category(self, period: str = "year") -> list[dict]:
        """توزيع الأرباح حسب التصنيف."""
        f, t = _period_range(period)
        rows = db.query_all(
            """
            SELECT
                p.category AS category,
                COALESCE(SUM(ii.total_profit), 0) AS profit
            FROM invoice_items ii
            JOIN products p ON p.id = ii.product_id
            JOIN invoices i ON i.id = ii.invoice_id
            WHERE i.status = 'archived'
              AND i.invoice_date BETWEEN ? AND ?
            GROUP BY p.category
            """,
            (f, t),
        )
        total = sum(r["profit"] for r in rows) or 1
        for r in rows:
            r["percent"] = (r["profit"] / total) * 100
        return rows


    def get_recent_invoices(self, limit: int = 5) -> list[dict]:
        return self._invoice_list("archived", limit)

    def get_draft_invoices(self) -> list[dict]:
        return self._invoice_list("draft")

    def _invoice_list(self, status: str, limit: int | None = None) -> list[dict]:
        order = "i.archived_at DESC, i.id DESC" if status == "archived" else "i.updated_at DESC, i.created_at DESC, i.id DESC"
        limit_sql = " LIMIT ?" if limit is not None else ""
        params = (status, limit) if limit is not None else (status,)
        return db.query_all(
            f"""
            SELECT i.id, i.invoice_no, i.supplier_invoice_no, i.invoice_date,
                   i.status, i.total_usd, i.total_profit, i.archived_at,
                   COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) AS supplier_name,
                   COALESCE((SELECT SUM(quantity) FROM invoice_items WHERE invoice_id = i.id), 0) AS total_qty
            FROM invoices i JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.status = ?
            ORDER BY {order}{limit_sql}
            """, params,
        )

    def get_top_suppliers(self, period: str = "year", limit: int = 5) -> list[dict]:
        """أفضل الموردين حسب الربح."""
        f, t = _period_range(period)
        rows = db.query_all(
            """
            SELECT
                s.name AS name,
                COALESCE(SUM(i.total_profit), 0) AS profit
            FROM invoices i
            JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.status = 'archived'
              AND i.invoice_date BETWEEN ? AND ?
            GROUP BY s.id
            ORDER BY profit DESC
            LIMIT ?
            """,
            (f, t, limit),
        )
        return rows

    def get_payments_vs_profit(self, period: str = "year") -> list[dict]:
        """المدفوعات مقابل الأرباح شهريًا."""
        f, t = _period_range(period)
        rows = db.query_all(
            """
            SELECT
                strftime('%Y-%m', invoice_date) AS ym,
                COALESCE(SUM(total_payments), 0) AS payments,
                COALESCE(SUM(total_profit), 0)   AS profit
            FROM invoices
            WHERE status = 'archived'
              AND invoice_date BETWEEN ? AND ?
            GROUP BY ym
            ORDER BY ym
            """,
            (f, t),
        )
        return [
            {"month": r["ym"], "payments": r["payments"], "profit": r["profit"]}
            for r in rows
        ]


# Singleton
dashboard_service = DashboardService()