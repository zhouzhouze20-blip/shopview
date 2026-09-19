from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import activity_analysis


def test_coupon_flow_query_limits_logs_before_aggregating_large_sales_tables():
    sql = activity_analysis._coupon_flows_query_sql(
        "1=1",
        "",
    )

    assert "filtered_logs AS MATERIALIZED" in sql
    assert sql.index("LIMIT :limit OFFSET :offset") < sql.index("FROM salepay")
    assert "WHERE p.billno = fl.billno" in sql
    assert "WHERE sgl.sglbillno = fl.billno" in sql
    assert "GROUP BY billno, batch" not in sql
    assert "GROUP BY sglbillno" not in sql
