import inspect
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import revenue


def test_revenue_recalculation_prefers_a_binding_with_a_mapped_unit():
    order_sql = " ".join(revenue.REVENUE_BINDING_ORDER_SQL.split())

    assert order_sql.startswith("(b.shop_unit_id IS NOT NULL) DESC")
    assert order_sql.index("b.shop_unit_id IS NOT NULL") < order_sql.index("b.is_primary")
    assert "ORDER BY {REVENUE_BINDING_ORDER_SQL}" in inspect.getsource(
        revenue.recalculate_revenue
    )


def test_live_revenue_source_reads_sales_directly_and_keeps_other_sources():
    sql = " ".join(
        revenue._live_revenue_source_ctes(
            "s.sgldate BETWEEN :start_date AND :end_date",
            "fee.revenue_date BETWEEN :start_date AND :end_date",
            "extra.revenue_date BETWEEN :start_date AND :end_date",
            "AND TRIM(s.sglmarket) = :store_code",
        ).split()
    )

    assert "FROM salegoodslist s" in sql
    assert "FROM unit_revenue_fee_detail fee" in sql
    assert "FROM revenue_extra_receipts extra" in sql
    assert "extra.status = 'CONFIRMED'" in sql
    assert "unit_daily_revenue_summary" not in sql
    assert "unit_revenue_sales_detail" not in sql
    assert "cg.store_id = st.store_id" in sql
    assert "TRIM(unit_floor.store_code) = sales_by_group.store_code" in sql
    assert "sales_by_group.store_code" in sql
    assert "(b.shop_unit_id IS NOT NULL) DESC" in sql


def test_map_queries_do_not_depend_on_recalculated_sales_tables():
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)

    assert "_live_revenue_source_ctes" in monthly_source
    assert "unit_daily_revenue_summary" not in monthly_source
    assert "unmatched_revenue_items" not in monthly_source
    assert "FROM sales_by_group source" in monthly_source
    assert "_live_revenue_source_ctes" in detail_source
    assert "_live_sales_ctes" in detail_source
    assert "unit_daily_revenue_summary" not in detail_source
    assert "unit_revenue_sales_detail" not in detail_source


def test_revenue_map_page_has_no_manual_recalculation_action():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")

    assert "useRecalculateRevenue" not in page_source
    assert "handleRecalculate" not in page_source
    assert ">重算<" not in page_source.replace(" ", "")
