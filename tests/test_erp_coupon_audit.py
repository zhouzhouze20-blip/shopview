import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reports'))
from audit_erp_coupon_primary_20260906 import compare_daily


def row(**changes):
    return dict(store='601', business_day='2026-08-31', n='2', unique_logs='2', key_sum='60', signed_amount='-1.10') | changes


def test_oracle_uppercase_and_exact_decimal_match():
    oracle = {k.upper(): v for k, v in row(signed_amount=-1.1).items()}
    assert compare_daily([oracle], [row()])['passed']


def test_equal_counts_do_not_hide_different_keys_or_amounts():
    assert not compare_daily([row()], [row(key_sum='61')])['passed']
    assert not compare_daily([row()], [row(signed_amount='1.10')])['passed']


def test_missing_day_is_explicit_not_omitted():
    result = compare_daily([row()], [])
    assert not result['passed']
    assert result['differences'][0]['count_gap'] == 2
    assert result['differences'][0]['target'] is None


def test_duplicate_group_refuses_silent_overwrite():
    with pytest.raises(ValueError, match='Duplicate'):
        compare_daily([row(), row()], [row()])
