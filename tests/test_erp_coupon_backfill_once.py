import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reports'))
from backfill_erp_coupon_once_20260906 import check, SCOPE


def task(**overrides):
    return dict(source_id=7,target_source_id=4,sql_text='reviewed',table_name='public.tktcardfqlog',
                insert_mode='skip',key_columns='tcflseqno',enabled=0,schedule_enabled=0,
                auto_create_table=0,watermark_enabled=0,max_rows=0) | overrides


def test_valid_insert_only_disabled_configuration():
    check(task(), {'sqlText':'reviewed','tableName':'public.tktcardfqlog'})


@pytest.mark.parametrize('change',[
    {'insert_mode':'update'}, {'enabled':1}, {'schedule_enabled':1},
    {'auto_create_table':1}, {'watermark_enabled':1}, {'max_rows':1000},
    {'source_id':14}, {'target_source_id':7}, {'key_columns':'tcflvipno'},
    {'sql_text':'unreviewed'}, {'table_name':'another_table'},
])
def test_unsafe_or_changed_configuration_is_rejected(change):
    with pytest.raises(AssertionError):
        check(task(**change), {'sqlText':'reviewed','tableName':'public.tktcardfqlog'})


def test_only_two_stores_and_two_historical_days():
    assert "TCFLMKT IN ('601','603')" in SCOPE
    assert "TCFLDATE >= DATE '2026-08-31' AND TCFLDATE < DATE '2026-09-01'" in SCOPE
    assert "TCFLDATE >= DATE '2026-09-05' AND TCFLDATE < DATE '2026-09-06'" in SCOPE
    assert '607' not in SCOPE
