"""CLI for validating and importing a confirmed revenue month-close workbook."""

from __future__ import annotations

import argparse
import json
from datetime import date

from models.database import engine
from services.revenue_month_close_import import import_month_close, parse_month_close_workbook


def main() -> int:
    parser = argparse.ArgumentParser(description="校验并导入收益看板月结快照")
    parser.add_argument("workbook")
    parser.add_argument("--store-code", required=True)
    parser.add_argument("--period-start", required=True, type=date.fromisoformat)
    parser.add_argument("--period-end", required=True, type=date.fromisoformat)
    parser.add_argument("--apply", action="store_true", help="确认写入；默认只校验")
    parser.add_argument(
        "--supersede",
        action="store_true",
        help="保留原快照为REOPENED并写入更正版本",
    )
    args = parser.parse_args()

    parsed = parse_month_close_workbook(args.workbook)
    result = {
        "status": "validated",
        "period_month": parsed.period_month,
        "source_snapshot_id": parsed.source_snapshot_id,
        "adjustment_rows": len(parsed.adjustments),
        "nc_control_amount": str(parsed.nc_control_amount),
        "raw_fee_amount": str(parsed.raw_fee_amount),
        "raw_extra_amount": str(parsed.raw_extra_amount),
        "close_adjustment_amount": str(parsed.close_adjustment_amount),
        "final_fee_extra_amount": str(parsed.final_fee_extra_amount),
    }
    if args.apply:
        result = import_month_close(
            engine,
            parsed,
            store_code=args.store_code,
            period_start_date=args.period_start,
            period_end_date=args.period_end,
            supersede_existing=args.supersede,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
