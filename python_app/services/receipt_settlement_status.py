"""Query local, atomically published ERP settlement snapshots only."""
from datetime import datetime,timezone
from sqlalchemy import text

MAX_AGE_SECONDS=3600


class SettlementStatusUnavailable(RuntimeError):
    pass


def sync_status(db, *, require_fresh=False):
    if not db.execute(text("SELECT to_regclass('cosmetics_receipt_settlement_sync')")).scalar():
        raise SettlementStatusUnavailable('验收单结算同步表尚未初始化')
    row=db.execute(text('SELECT source_at,published_at,row_count FROM cosmetics_receipt_settlement_sync WHERE singleton=true')).mappings().first()
    if not row:
        raise SettlementStatusUnavailable('验收单结算数据尚未完成首次同步，请稍后刷新')
    age=(datetime.now(timezone.utc)-row['source_at']).total_seconds()
    stale=age>MAX_AGE_SECONDS or age < -300
    if require_fresh and stale:
        raise SettlementStatusUnavailable('验收单结算数据超过1小时未更新，暂不能生成配票单，请等待同步恢复')
    return dict(source_at=row['source_at'].isoformat(),published_at=row['published_at'].isoformat(),
                row_count=row['row_count'],stale=stale,max_age_minutes=60)


def unassociated_receipt_numbers(db,store,supplier,numbers,*,require_fresh=False):
    sync_status(db,require_fresh=require_fresh)
    if not numbers:
        return set()
    return set(db.execute(text('''SELECT receipt_number FROM cosmetics_receipt_settlement_state
        WHERE store_code=:store AND supplier_code=:supplier AND receipt_number=ANY(:numbers)
          AND linked_rows=0'''),dict(store=store,supplier=supplier,numbers=list(numbers))).scalars())
