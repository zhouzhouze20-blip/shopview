"""Evaluate the purchase alias as SQL without requiring a database server.

The alias predicate uses only standard SQL equality, TRIM and LIKE. SQLite
can execute these fixtures; the complete PostgreSQL query is verified against
the source voucher rows separately.
"""

import sqlite3
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.activity_analysis import credit_buy_voucher_alias_sql


def matches_alias(**overrides):
    values = {
        "match_type": "CREDIT_BUY",
        "market_code": "603",
        "coupon_type": "D",
        "business_store": "105",
        "business_date": "2026-08-07",
        "voucher_corp_code": "1021",
        "subject_code": "122104",
        "voucher_store": "105",
        "voucher_date": "2026-08-07",
        "explanation": "(105)20260807销售收入0580增值卡",
    }
    values.update(overrides)
    with sqlite3.connect(":memory:") as db:
        row = db.execute(
            f"""
            WITH br AS (
              SELECT :match_type AS match_type, :market_code AS market_code,
                     :coupon_type AS coupon_type,
                     :business_store AS voucher_store_code,
                     :business_date AS business_date
            ), v AS (
              SELECT :voucher_corp_code AS voucher_corp_code,
                     :subject_code AS subject_code,
                     :voucher_store AS voucher_store_code,
                     :voucher_date AS voucher_business_date,
                     :explanation AS explanation
            )
            SELECT CASE WHEN {credit_buy_voucher_alias_sql()} THEN 1 ELSE 0 END
            FROM br CROSS JOIN v
            """,
            values,
        ).fetchone()
    return bool(row[0])


@pytest.mark.parametrize("day", ["07", "08", "09"])
def test_new_century_d_purchase_recognizes_nc_value_card_label(day):
    assert matches_alias(
        business_date=f"2026-08-{day}",
        voucher_date=f"2026-08-{day}",
        explanation=f"(105)202608{day}销售收入0580增值卡",
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"match_type": "DEBIT_USE"},
        {"market_code": "601"},
        {"coupon_type": "C"},
        {"voucher_corp_code": "1018"},
        {"subject_code": "112201"},
        {"voucher_store": "101"},
        {"voucher_store": None},
        {"voucher_date": "2026-08-08"},
        {"voucher_date": None},
        {"explanation": "(105)20260807销售收入0580增值卡3"},
        {"explanation": "(105)20260807销售收入其他增值卡"},
        {"explanation": "(105)20260807销售收入0580增值卡退款"},
        {"explanation": "(105)20260807销售收入0580增值卡扣回"},
        {"explanation": "(105)20260807调整0580增值卡"},
        {"explanation": None},
    ],
)
def test_alias_does_not_match_other_business_or_ambiguous_vouchers(overrides):
    assert not matches_alias(**overrides)


def test_alias_tolerates_surrounding_summary_spaces():
    assert matches_alias(explanation="  (105)20260807销售收入0580增值卡  ")
