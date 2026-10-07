"""
خدمة التقارير — تجمع بيانات التقارير الستة.
"""
from datetime import date, timedelta

from app.db import db


def _period_range(period: str) -> tuple[str, str]:
    today = date.today()
    to_str = today.isoformat()
    if period == "month":
        from_str = today.replace(day=1).isoformat()
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        from_str = today.replace(month=q_start_month, day=1).isoformat()
    elif period == "year":
        from_str = today.replace(month=1, day=1).isoformat()
    elif period == "all":
        from_str = "1900-01-01"
    else:
        from_str = today.replace(month=1, day=1).isoformat()
    return from_str, to_str


class ReportsService:

    # ============================================================
    # 1) تقرير المورد
    # ============================================================
    def supplier_report(self, supplier_id: int, period: str = "year") -> dict:
        f, t = _period_range(period)

        stats = db.query_one(
            """
            SELECT
                COUNT(*) AS invoices_count,
                COALESCE(SUM(total_payments), 0) AS total_payments,
                COALESCE(SUM(total_usd), 0)      AS total_usd,
                COALESCE(SUM(total_profit), 0)   AS total_profit
            FROM invoices
            WHERE supplier_id = ? AND status = 'archived'
              AND invoice_date BETWEEN ? AND ?
            """,
            (supplier_id, f, t),
        ) or {}

        invoices = db.query_all(
            """
            SELECT
                i.invoice_no, i.invoice_date, i.total_usd, i.total_profit,
                i.net_cost,
                (SELECT COALESCE(SUM(quantity), 0) FROM invoice_items
                  WHERE invoice_id = i.id) AS total_qty
            FROM invoices i
            WHERE i.supplier_id = ? AND i.status = 'archived'
              AND i.invoice_date BETWEEN ? AND ?
            ORDER BY i.invoice_date DESC
            """,
            (supplier_id, f, t),
        )

        trend = db.query_all(
            """
            SELECT strftime('%Y-%m', invoice_date) AS ym,
                   COALESCE(SUM(total_profit), 0) AS profit
            FROM invoices
            WHERE supplier_id = ? AND status = 'archived'
              AND invoice_date BETWEEN ? AND ?
            GROUP BY ym ORDER BY ym
            """,
            (supplier_id, f, t),
        )

        return {
            "stats": {
                "invoices_count": stats.get("invoices_count", 0),
                "total_payments": stats.get("total_payments", 0),
                "total_usd":      stats.get("total_usd", 0),
                "total_profit":   stats.get("total_profit", 0),
            },
            "invoices": invoices,
            "trend": [{"month": r["ym"], "value": r["profit"]} for r in trend],
        }

    # ============================================================
    # 2) تقرير الأرباح
    # ============================================================
    def profit_report(self, period: str = "year", supplier_id=None) -> dict:
        f, t = _period_range(period)

        conditions = ["status = 'archived'", "invoice_date BETWEEN ? AND ?"]
        params = [f, t]
        if supplier_id:
            conditions.append("supplier_id = ?")
            params.append(supplier_id)
        where = " AND ".join(conditions)

        join_conditions = ["i.status = 'archived'",
                           "i.invoice_date BETWEEN ? AND ?"]
        if supplier_id:
            join_conditions.append("i.supplier_id = ?")
        join_where = " AND ".join(join_conditions)

        stats = db.query_one(
            f"""
            SELECT
                COUNT(*) AS invoices_count,
                COALESCE(SUM(total_sales), 0)   AS total_sales,
                COALESCE(SUM(total_profit), 0)  AS total_profit,
                COALESCE(AVG(profit_margin), 0) AS avg_margin
            FROM invoices WHERE {where}
            """,
            tuple(params),
        ) or {}

        invoices = db.query_all(
            f"""
            SELECT i.invoice_no, i.invoice_date,
                   COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) AS supplier_name,
                   i.total_profit, i.profit_margin
            FROM invoices i
            JOIN suppliers s ON s.id = i.supplier_id
            WHERE {join_where}
            ORDER BY i.invoice_date DESC
            """,
            tuple(params),
        )

        monthly = db.query_all(
            f"""
            SELECT strftime('%Y-%m', invoice_date) AS ym,
                   COALESCE(SUM(total_profit), 0) AS profit
            FROM invoices WHERE {where}
            GROUP BY ym ORDER BY ym
            """,
            tuple(params),
        )

        return {
            "stats": {
                "invoices_count": stats.get("invoices_count", 0),
                "total_sales":    stats.get("total_sales", 0),
                "total_profit":   stats.get("total_profit", 0),
                "avg_margin":     stats.get("avg_margin", 0),
            },
            "invoices": invoices,
            "monthly": [{"month": r["ym"], "value": r["profit"]} for r in monthly],
        }

    # ============================================================
    # 3) تقرير الفترة
    # ============================================================
    def period_report(self, date_from: str, date_to: str,
                      supplier_id=None) -> dict:
        conditions = ["i.status = 'archived'",
                      "i.invoice_date BETWEEN ? AND ?"]
        params = [date_from, date_to]
        if supplier_id:
            conditions.append("i.supplier_id = ?")
            params.append(supplier_id)
        where = " AND ".join(conditions)

        stats = db.query_one(
            f"""
            SELECT
                COUNT(*) AS invoices_count,
                COALESCE(SUM(i.total_payments), 0) AS total_payments,
                COALESCE(SUM(i.total_usd), 0)      AS total_usd,
                COALESCE(SUM(i.total_profit), 0)   AS total_profit
            FROM invoices i WHERE {where}
            """,
            tuple(params),
        ) or {}

        invoices = db.query_all(
            f"""
            SELECT i.invoice_no, i.invoice_date, i.total_usd,
                   i.total_profit, COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) AS supplier_name
            FROM invoices i
            JOIN suppliers s ON s.id = i.supplier_id
            WHERE {where}
            ORDER BY i.invoice_date DESC
            """,
            tuple(params),
        )

        daily = db.query_all(
            f"""
            SELECT i.invoice_date AS d,
                   COALESCE(SUM(i.total_profit), 0) AS profit
            FROM invoices i
            WHERE {where}
            GROUP BY d ORDER BY d
            """,
            tuple(params),
        )

        return {
            "stats": {
                "invoices_count": stats.get("invoices_count", 0),
                "total_payments": stats.get("total_payments", 0),
                "total_usd":      stats.get("total_usd", 0),
                "total_profit":   stats.get("total_profit", 0),
            },
            "invoices": invoices,
            "daily": [{"date": r["d"], "value": r["profit"]} for r in daily],
        }

    # ============================================================
    # 4) تقرير تغيّر الأسعار
    # ============================================================
    def price_changes_report(self, product_id: int, period: str = "year") -> dict:
        f, t = _period_range(period)

        history = db.query_all(
            """
            SELECT i.invoice_date AS date,
                   i.invoice_no,
                   COALESCE(json_extract(i.archived_snapshot, '$.supplier_name'), s.name) AS supplier_name,
                   ii.purchase_usd, ii.sale_dzd
            FROM invoice_items ii
            JOIN invoices i ON i.id = ii.invoice_id
            JOIN suppliers s ON s.id = i.supplier_id
            WHERE ii.product_id = ? AND i.status = 'archived'
              AND i.invoice_date BETWEEN ? AND ?
            ORDER BY i.invoice_date ASC
            """,
            (product_id, f, t),
        )

        changes = []
        prev_pu = None
        prev_sd = None
        for h in history:
            pu = h["purchase_usd"] or 0
            sd = h["sale_dzd"] or 0
            ch_pu = None
            ch_sd = None
            if prev_pu and prev_pu > 0:
                ch_pu = ((pu - prev_pu) / prev_pu) * 100
            if prev_sd and prev_sd > 0:
                ch_sd = ((sd - prev_sd) / prev_sd) * 100
            changes.append({
                "date": h["date"],
                "invoice_no": h["invoice_no"],
                "supplier_name": h["supplier_name"],
                "purchase_usd": pu,
                "sale_dzd": sd,
                "change_purchase": ch_pu,
                "change_sale": ch_sd,
            })
            prev_pu = pu
            prev_sd = sd

        return {
            "stats": {
                "last_purchase": changes[-1]["purchase_usd"] if changes else 0,
                "last_sale":     changes[-1]["sale_dzd"] if changes else 0,
                "first_purchase": changes[0]["purchase_usd"] if changes else 0,
                "first_sale":    changes[0]["sale_dzd"] if changes else 0,
            },
            "changes": changes,
        }

    # ============================================================
    # 5) تقرير الأكثر ربحية — يدعم top_n=0 (الكل)
    # ============================================================
    def most_profitable_report(self, period: str = "year",
                               category: str = "", top_n: int = 10) -> dict:
        f, t = _period_range(period)

        conditions = ["i.status = 'archived'", "i.invoice_date BETWEEN ? AND ?"]
        params = [f, t]
        if category:
            conditions.append("p.category = ?")
            params.append(category)
        where = " AND ".join(conditions)

        # ✅ دعم top_n=0 → الكل
        limit_clause = ""
        query_params = list(params)
        if top_n and top_n > 0:
            limit_clause = "LIMIT ?"
            query_params.append(top_n)

        rows = db.query_all(
            f"""
            SELECT p.id, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS code, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS name, p.category, p.pattern,
                   COALESCE(SUM(ii.quantity), 0) AS total_qty,
                   COALESCE(SUM(ii.total_sale), 0) AS total_sales,
                   COALESCE(SUM(ii.total_profit), 0) AS total_profit
            FROM invoice_items ii
            JOIN products p ON p.id = ii.product_id
            JOIN invoices i ON i.id = ii.invoice_id
            WHERE {where}
            GROUP BY p.id
            ORDER BY total_profit DESC
            {limit_clause}
            """,
            tuple(query_params),
        )

        for r in rows:
            r["margin"] = (r["total_profit"] / r["total_sales"] * 100) if r["total_sales"] else 0

        total_profit = sum(r["total_profit"] for r in rows)
        avg_margin = sum(r["margin"] for r in rows) / len(rows) if rows else 0
        top_profit = rows[0]["total_profit"] if rows else 0

        return {
            "stats": {
                "total_profit": total_profit,
                "products_count": len(rows),
                "avg_margin": avg_margin,
                "top_profit": top_profit,
            },
            "products": rows,
        }

    # ============================================================
    # 6) تقرير الأكثر مبيعًا — يدعم top_n=0 (الكل)
    # ============================================================
    def best_selling_report(self, period: str = "year",
                            category: str = "", top_n: int = 10) -> dict:
        f, t = _period_range(period)

        conditions = ["i.status = 'archived'", "i.invoice_date BETWEEN ? AND ?"]
        params = [f, t]
        if category:
            conditions.append("p.category = ?")
            params.append(category)
        where = " AND ".join(conditions)

        # ✅ دعم top_n=0 → الكل
        limit_clause = ""
        query_params = list(params)
        if top_n and top_n > 0:
            limit_clause = "LIMIT ?"
            query_params.append(top_n)

        rows = db.query_all(
            f"""
            SELECT p.id, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS code, CASE WHEN p.category = 'Batteries' THEN p.code ELSE p.name END AS name, p.category, p.pattern,
                   COALESCE(SUM(ii.quantity), 0) AS total_qty,
                   COALESCE(SUM(ii.total_sale), 0) AS total_sales,
                   COUNT(DISTINCT i.id) AS invoices_count
            FROM invoice_items ii
            JOIN products p ON p.id = ii.product_id
            JOIN invoices i ON i.id = ii.invoice_id
            WHERE {where}
            GROUP BY p.id
            ORDER BY total_qty DESC
            {limit_clause}
            """,
            tuple(query_params),
        )

        total_qty = sum(r["total_qty"] for r in rows)
        total_sales = sum(r["total_sales"] for r in rows)
        top_qty = rows[0]["total_qty"] if rows else 0

        return {
            "stats": {
                "total_qty": total_qty,
                "total_sales": total_sales,
                "top_qty": top_qty,
                "products_count": len(rows),
            },
            "products": rows,
        }


reports_service = ReportsService()