"""Self-operated store data; independent of the four department-store sources."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import hashlib
import json

from openpyxl import load_workbook
from sqlalchemy import (MetaData, Table, Column, Integer, String, Date, DateTime, case,
                        Numeric, JSON, ForeignKey, Index, select, delete, func, text)
from sqlalchemy.dialects.postgresql import JSONB

from services.fungkids_retail_import import parse_export

STORE_CODE = "SELF_OPERATED"
RESOURCE_CODE = "self_operated_sales"
SECTIONS = {"CLOTHING": "自营服装", "BAKERY": "自营餐饮"}
STORE_DISPLAY_NAMES = {"PBCZ6001": "购物中心小帆船"}
metadata = MetaData()
imports = Table("self_operated_sales_imports", metadata,
    Column("id", Integer, primary_key=True),
    Column("source_file", String(255), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("channel", String(50), nullable=False),
    Column("section", String(20), nullable=False),
    Column("start_date", Date, nullable=False), Column("end_date", Date, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("imported_by", String(100)),
    Column("row_count", Integer, nullable=False),
    Column("sales", Numeric(18, 2), nullable=False))
lines = Table("self_operated_sales_lines", metadata,
    Column("id", Integer, primary_key=True),
    Column("import_id", ForeignKey(imports.c.id), nullable=False),
    Column("source_row", Integer, nullable=False),
    Column("section", String(20), nullable=False), Column("channel", String(50), nullable=False),
    Column("business_date", Date, nullable=False), Column("bill", String(100), nullable=False),
    Column("original_bill", String(100)), Column("product", String(100), nullable=False),
    Column("product_name", String(255)), Column("color", String(100)), Column("size", String(100)),
    Column("sale_type", String(20), nullable=False), Column("quantity", Numeric(18, 4), nullable=False),
    Column("sales", Numeric(18, 2), nullable=False), Column("discount", Numeric(12, 8), nullable=False),
    Column("supplier_rate", Numeric(6, 4), nullable=False),
    Column("supplier_cost", Numeric(18, 2), nullable=False), Column("venue_fee", Numeric(18, 2), nullable=False),
    Column("expected_receipt", Numeric(18, 2), nullable=False), Column("gross_profit", Numeric(18, 2), nullable=False),
    Column("source_data", JSON().with_variant(JSONB, "postgresql"), nullable=False))
Index("ix_self_operated_sales_scope_date", lines.c.section, lines.c.channel, lines.c.business_date)
coverage = Table("self_operated_sales_coverage", metadata,
    Column("section", String(20), primary_key=True), Column("channel", String(50), primary_key=True),
    Column("business_date", Date, primary_key=True), Column("import_id", ForeignKey(imports.c.id), nullable=False))
MONEY_FIELDS = ("sales", "venue_fee", "expected_receipt", "supplier_cost", "gross_profit")


def read_discount_settlement(db, start, end, channel=None):
    """Clothing contract bands; sum signed, already rounded line settlements."""
    band = case((lines.c.discount >= Decimal("0.85"), 0),
                (lines.c.discount >= Decimal("0.70"), 1), else_=2)
    filters = [lines.c.section == "CLOTHING", lines.c.business_date.between(start, end)]
    if channel is not None:
        filters.append(lines.c.channel == channel)
    grouped = db.execute(select(band.label("band"), func.sum(lines.c.sales).label("sales"),
        func.sum(lines.c.supplier_cost).label("remittance")).where(*filters).group_by(band)).mappings().all()
    values = {row["band"]: row for row in grouped}
    rows = []
    for index, (label, rate) in enumerate((("折扣 ≥85%", "0.50"),
            ("70% ≤折扣 <85%", "0.52"), ("折扣 <70%", "0.55"))):
        value = values.get(index, {})
        rows.append(dict(label=label, rate=Decimal(rate), sales=value.get("sales", Decimal(0)),
                         remittance=value.get("remittance", Decimal(0))))
    sales = sum((row["sales"] for row in rows), Decimal(0))
    remittance = sum((row["remittance"] for row in rows), Decimal(0))
    for row in rows:
        row["our_settlement"] = row["sales"] - row["remittance"]
        row["sales_share"] = row["sales"] / sales if sales else None
    scope = section_summary(db, "CLOTHING", start, end, channel)
    return dict(start_date=start, end_date=end, channel=channel, rows=rows,
                totals=dict(sales=sales, remittance=remittance, our_settlement=sales-remittance,
                            sales_share=Decimal(1) if sales else None),
                coverage=scope["coverage"])


def publish_export(engine, path, *, start, end, source_file=None, imported_by=None):
    """Transactionally replace an explicitly declared complete channel/date export."""
    path = Path(path)
    parsed = parse_export(path, start=start, end=end)
    if not parsed.lines:
        raise ValueError("空文件不能覆盖数据库数据")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != parsed.sha256:
        raise ValueError("导入期间文件发生变化")
    book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        rows = list(book["店铺零售报表"].values)
    finally:
        book.close()
    raw_rows = {i: dict(zip(rows[0], values)) for i, values in enumerate(rows[1:], 2)}
    with engine.begin() as db:
        if engine.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(1849202609)"))
        batch_id = db.execute(imports.insert().values(source_file=source_file or path.name, imported_by=imported_by,
            sha256=parsed.sha256, channel=parsed.channel, section="CLOTHING",
            start_date=start, end_date=end, imported_at=datetime.now(timezone.utc),
            row_count=len(parsed.lines), sales=sum(row.sales for row in parsed.lines))).inserted_primary_key[0]
        for table in (lines, coverage):
            db.execute(delete(table).where(table.c.channel == parsed.channel,
                table.c.section == "CLOTHING", table.c.business_date.between(start, end)))
        values = []
        for row in parsed.lines:
            raw = raw_rows[row.source_row]
            values.append(dict(import_id=batch_id, source_row=row.source_row, section="CLOTHING",
                channel=row.channel, business_date=date.fromisoformat(row.business_date),
                bill=row.bill, original_bill=row.original_bill, product=row.product,
                product_name=raw.get("品名"), color=raw.get("颜色名称"), size=str(raw.get("尺码") or ""),
                sale_type=row.sale_type, quantity=row.quantity, discount=row.discount,
                supplier_rate=row.supplier_rate, **{key: getattr(row, key) for key in MONEY_FIELDS},
                source_data=json.loads(json.dumps(raw, default=str, ensure_ascii=False))))
        db.execute(lines.insert(), values)
        db.execute(coverage.insert(), [dict(section="CLOTHING", channel=parsed.channel,
            business_date=start+timedelta(days=i), import_id=batch_id)
            for i in range((end-start).days+1)])
    return {"import_id": batch_id, **parsed.summary()}


def section_summary(db, section, start, end, channel=None):
    filters = [lines.c.section == section, lines.c.business_date.between(start, end)]
    coverage_filters = [coverage.c.section == section]
    import_filters = [imports.c.section == section]
    if channel is not None:
        filters.append(lines.c.channel == channel)
        coverage_filters.append(coverage.c.channel == channel)
        import_filters.append(imports.c.channel == channel)
    amounts = db.execute(select(*[func.coalesce(func.sum(lines.c[key]), 0).label(key)
        for key in MONEY_FIELDS], func.count().label("row_count"),
        func.count(func.distinct(lines.c.bill)).label("ticket_count"),
        func.coalesce(func.sum(lines.c.quantity), 0).label("quantity")).where(*filters)).mappings().one()
    latest = db.execute(select(imports.c.imported_at).where(*import_filters)
                        .order_by(imports.c.id.desc()).limit(1)).scalar()
    imported = db.execute(select(func.min(coverage.c.business_date), func.max(coverage.c.business_date))
                          .where(*coverage_filters)).one()
    days = db.execute(select(func.count(func.distinct(coverage.c.business_date))).where(
        *coverage_filters, coverage.c.business_date.between(start, end))).scalar()
    state = "not_imported" if not days else ("complete" if days == (end-start).days+1 else "partial")
    ticket_keys = select(lines.c.channel, lines.c.business_date, lines.c.bill).where(*filters).distinct().subquery()
    amounts = dict(amounts)
    amounts["ticket_count"] = db.execute(select(func.count()).select_from(ticket_keys)).scalar()
    return dict(code=section, name=SECTIONS[section], **amounts, coverage=state,
                covered_days=days, requested_days=(end-start).days+1,
                imported_start=imported[0], imported_end=imported[1], imported_at=latest)


def read_summary(db, allowed, start, end):
    sections = [section_summary(db, code, start, end) for code in allowed]
    for item in sections:
        channels = db.execute(select(coverage.c.channel).where(coverage.c.section == item["code"]).distinct()).scalars().all()
        item["stores"] = []
        for channel in sorted(channels):
            store = section_summary(db, item["code"], start, end, channel)
            name = db.execute(select(lines.c.source_data["渠道简称"].as_string()).where(
                lines.c.section == item["code"], lines.c.channel == channel).order_by(lines.c.id.desc()).limit(1)).scalar()
            store.update(channel=channel, name=STORE_DISPLAY_NAMES.get(channel, name or channel))
            item["stores"].append(store)
        if item["stores"]:
            states = [store["coverage"] for store in item["stores"]]
            item["coverage"] = "complete" if all(state == "complete" for state in states) else (
                "not_imported" if all(state == "not_imported" for state in states) else "partial")
    totals = {key: sum((row[key] for row in sections), Decimal(0)) for key in MONEY_FIELDS}
    return {"store_code": STORE_CODE, "store_name": "自营公司", "sections": sections,
            "totals": totals, "start_date": start, "end_date": end}


def read_details(db, section, start, end, offset=0, limit=50):
    # Deliberately exclude source_data, which may contain member contact fields.
    columns = [lines.c[key] for key in ("id", "business_date", "bill", "original_bill", "product",
        "product_name", "color", "size", "sale_type", "quantity", "discount", "supplier_rate", *MONEY_FIELDS)]
    condition = (lines.c.section == section, lines.c.business_date.between(start, end))
    count = db.execute(select(func.count()).select_from(lines).where(*condition)).scalar()
    rows = db.execute(select(*columns).where(*condition).order_by(
        lines.c.business_date.desc(), lines.c.bill, lines.c.source_row).offset(offset).limit(limit)).mappings().all()
    return {"total": count, "offset": offset, "limit": limit, "rows": [dict(row) for row in rows]}


def read_tickets(db, section, channel, start, end, offset=0, limit=20):
    """Page whole tickets, retaining every signed product line and duplicate source row."""
    filters = (lines.c.section == section, lines.c.channel == channel,
               lines.c.business_date.between(start, end))
    grouped = select(lines.c.business_date, lines.c.bill,
        *[func.sum(lines.c[key]).label(key) for key in MONEY_FIELDS],
        func.sum(lines.c.quantity).label("quantity"), func.count().label("row_count")
    ).where(*filters).group_by(lines.c.business_date, lines.c.bill)
    total = db.execute(select(func.count()).select_from(grouped.subquery())).scalar()
    tickets = db.execute(grouped.order_by(lines.c.business_date.desc(), lines.c.bill)
                         .offset(offset).limit(limit)).mappings().all()
    columns = [col for col in lines.c if col.name not in ("source_data",)]
    columns.append(lines.c.source_data["吊牌价"].as_string().label("tag_price"))
    result = []
    for ticket in tickets:
        rows = db.execute(select(*columns).where(*filters,
            lines.c.business_date == ticket["business_date"], lines.c.bill == ticket["bill"])
            .order_by(lines.c.source_row, lines.c.id)).mappings().all()
        result.append({**ticket, "rows": [dict(row) for row in rows]})
    return {"total": total, "offset": offset, "limit": limit, "tickets": result}
