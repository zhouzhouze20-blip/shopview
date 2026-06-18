"""
收益地图与经营单元日收益 API。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission


router = APIRouter(prefix="/api/revenue-map", tags=["revenue"])


def _money(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _dt(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _month_from_date(value: date) -> str:
    return value.strftime("%Y-%m")


def _model_data(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class RevenueExtraReceiptCreate(BaseModel):
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    store_id: Optional[int] = None
    floor_id: Optional[int] = None
    revenue_date: date
    extra_type: str = Field(default="其他收益", max_length=100)
    amount: Decimal
    receipt_date: Optional[date] = None
    voucher_no: Optional[str] = None
    contract_code: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    source_group_code: Optional[str] = None
    source_group_name: Optional[str] = None
    remark: Optional[str] = None
    attachment_url: Optional[str] = None


class RevenueExtraReceiptUpdate(BaseModel):
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    store_id: Optional[int] = None
    floor_id: Optional[int] = None
    revenue_date: Optional[date] = None
    extra_type: Optional[str] = Field(default=None, max_length=100)
    amount: Optional[Decimal] = None
    receipt_date: Optional[date] = None
    voucher_no: Optional[str] = None
    contract_code: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    source_group_code: Optional[str] = None
    source_group_name: Optional[str] = None
    remark: Optional[str] = None
    attachment_url: Optional[str] = None


class RevenueRecalculateRequest(BaseModel):
    start_date: date
    end_date: date
    unit_id: Optional[int] = None


def _normalize_unit_fields(db: Session, payload: dict) -> dict:
    unit_id = payload.get("unit_id")
    if unit_id:
        row = db.execute(
            text(
                """
                SELECT id, floor_id, unit_code
                FROM business_units
                WHERE id = :unit_id
                """
            ),
            {"unit_id": unit_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="经营单元不存在")
        payload["unit_id"] = int(row.id)
        payload["unit_code"] = payload.get("unit_code") or row.unit_code
        payload["floor_id"] = payload.get("floor_id") or int(row.floor_id)
    if not payload.get("unit_id") and not (payload.get("unit_code") or "").strip():
        raise HTTPException(status_code=400, detail="unit_id 或 unit_code 至少填写一个")
    return payload


def _receipt_to_dict(row) -> dict:
    return {
        "id": int(row.id),
        "store_id": row.store_id,
        "floor_id": row.floor_id,
        "unit_id": row.unit_id,
        "unit_code": row.unit_code,
        "revenue_date": _dt(row.revenue_date),
        "revenue_month": row.revenue_month,
        "extra_type": row.extra_type,
        "amount": _money(row.amount),
        "receipt_date": _dt(row.receipt_date),
        "voucher_no": row.voucher_no,
        "contract_code": row.contract_code,
        "supplier_code": row.supplier_code,
        "supplier_name": row.supplier_name,
        "source_group_code": row.source_group_code,
        "source_group_name": row.source_group_name,
        "remark": row.remark,
        "attachment_url": row.attachment_url,
        "status": row.status,
        "created_by": row.created_by,
        "confirmed_by": row.confirmed_by,
        "voided_by": row.voided_by,
        "confirmed_at": _dt(row.confirmed_at),
        "voided_at": _dt(row.voided_at),
        "created_at": _dt(row.created_at),
        "updated_at": _dt(row.updated_at),
    }


@router.get("/monthly")
async def monthly_revenue(
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    revenue_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    metric: str = Query("total", regex=r"^(total|sales|fee|extra)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if not (start_date and end_date) and not revenue_date and not revenue_month:
        raise HTTPException(status_code=400, detail="请传 start_date/end_date、revenue_date 或 revenue_month")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")
    try:
        params: dict = {}
        filters: list[str] = []
        unmatched_filters = ["status = 'PENDING'"]
        if start_date and end_date:
            params["start_date"] = start_date
            params["end_date"] = end_date
            filters.append("s.revenue_date BETWEEN :start_date AND :end_date")
            unmatched_filters.append("revenue_date BETWEEN :start_date AND :end_date")
            effective_month = _month_from_date(start_date)
        elif revenue_date:
            params["revenue_date"] = revenue_date
            filters.append("s.revenue_date = :revenue_date")
            unmatched_filters.append("revenue_date = :revenue_date")
            effective_month = _month_from_date(revenue_date)
        else:
            params["revenue_month"] = revenue_month
            filters.append("s.revenue_month = :revenue_month")
            unmatched_filters.append("revenue_month = :revenue_month")
            effective_month = revenue_month
        if store_id is not None:
            params["store_id"] = store_id
            store_row = db.execute(
                text("SELECT store_code FROM stores WHERE store_id = :store_id"),
                {"store_id": store_id},
            ).fetchone()
            store_code = str(store_row.store_code).strip() if store_row and store_row.store_code is not None else ""
            if store_code.isdigit():
                params["store_code_id"] = int(store_code)
                filters.append("(s.store_id = :store_id OR s.store_id = :store_code_id)")
                unmatched_filters.append("(store_id = :store_id OR store_id = :store_code_id)")
            else:
                filters.append("s.store_id = :store_id")
                unmatched_filters.append("store_id = :store_id")
        if floor_id is not None:
            filters.append("s.floor_id = :floor_id")
            params["floor_id"] = floor_id

        sql = f"""
            SELECT
              s.unit_id,
              s.unit_code,
              s.store_id,
              s.floor_id,
              bu.status AS unit_status,
              SUM(s.sales_gross_profit_amount)::numeric AS sales_gross_profit_amount,
              SUM(s.fee_amount)::numeric AS fee_amount,
              SUM(s.extra_amount)::numeric AS extra_amount,
              SUM(s.total_amount)::numeric AS total_amount,
              SUM(s.sales_detail_count)::bigint AS sales_detail_count,
              SUM(s.fee_detail_count)::bigint AS fee_detail_count,
              SUM(s.extra_detail_count)::bigint AS extra_detail_count
            FROM unit_daily_revenue_summary s
            LEFT JOIN business_units bu ON bu.id = s.unit_id
            WHERE {" AND ".join(filters)}
            GROUP BY s.unit_id, s.unit_code, s.store_id, s.floor_id, bu.status
            ORDER BY total_amount DESC, s.unit_code ASC
        """
        rows = db.execute(text(sql), params).fetchall()
        metric_key = {
            "total": "total_amount",
            "sales": "sales_gross_profit_amount",
            "fee": "fee_amount",
            "extra": "extra_amount",
        }[metric]
        items = []
        for row in rows:
            item = {
                "unit_id": row.unit_id,
                "unit_code": row.unit_code,
                "store_id": row.store_id,
                "floor_id": row.floor_id,
                "unit_status": row.unit_status,
                "sales_gross_profit_amount": _money(row.sales_gross_profit_amount),
                "fee_amount": _money(row.fee_amount),
                "extra_amount": _money(row.extra_amount),
                "total_amount": _money(row.total_amount),
                "sales_detail_count": int(row.sales_detail_count or 0),
                "fee_detail_count": int(row.fee_detail_count or 0),
                "extra_detail_count": int(row.extra_detail_count or 0),
            }
            item["metric_amount"] = item[metric_key]
            items.append(item)

        unmatched = db.execute(
            text(
                f"""
                SELECT
                  COUNT(*)::bigint AS item_count,
                  COALESCE(SUM(amount), 0)::numeric AS amount
                FROM unmatched_revenue_items
                WHERE {" AND ".join(unmatched_filters)}
                """
            ),
            params,
        ).fetchone()
        return {
            "revenue_month": effective_month,
            "revenue_date": _dt(revenue_date) if revenue_date else None,
            "start_date": _dt(start_date) if start_date else (_dt(revenue_date) if revenue_date else None),
            "end_date": _dt(end_date) if end_date else (_dt(revenue_date) if revenue_date else None),
            "metric": metric,
            "items": items,
            "unmatched": {
                "item_count": int(unmatched.item_count or 0) if unmatched else 0,
                "amount": _money(unmatched.amount) if unmatched else 0.0,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取收益汇总失败: {exc}")


@router.get("/units/{unit_id}/detail")
async def unit_revenue_detail(
    unit_id: int,
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if revenue_month:
        date_filter = "revenue_month = :revenue_month"
        params: dict = {"unit_id": unit_id, "revenue_month": revenue_month}
    elif start_date and end_date:
        date_filter = "revenue_date BETWEEN :start_date AND :end_date"
        params = {"unit_id": unit_id, "start_date": start_date, "end_date": end_date}
    else:
        raise HTTPException(status_code=400, detail="请传 revenue_month 或 start_date/end_date")

    try:
        unit = db.execute(
            text("SELECT id, floor_id, unit_code, status FROM business_units WHERE id = :unit_id"),
            {"unit_id": unit_id},
        ).fetchone()
        if not unit:
            raise HTTPException(status_code=404, detail="经营单元不存在")

        daily = db.execute(
            text(
                f"""
                SELECT revenue_date, revenue_month, sales_gross_profit_amount, fee_amount,
                       extra_amount, total_amount, sales_detail_count, fee_detail_count,
                       extra_detail_count
                FROM unit_daily_revenue_summary
                WHERE unit_id = :unit_id AND {date_filter}
                ORDER BY revenue_date ASC
                """
            ),
            params,
        ).fetchall()
        sales = db.execute(
            text(
                f"""
                SELECT id, revenue_date, revenue_month, source_group_code, source_group_name,
                       operation_mode, supplier_code, supplier_name, contract_code,
                       sales_qty, tax_excluded_sales_amount, tax_excluded_profit_amount,
                       source_doc_no, etl_batch_id
                FROM unit_revenue_sales_detail
                WHERE unit_id = :unit_id AND {date_filter}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        fees = db.execute(
            text(
                f"""
                SELECT id, revenue_date, revenue_month, source_group_code, source_group_name,
                       contract_code, contract_name, fee_type_code, fee_type_name,
                       tax_included_amount, tax_excluded_amount, source_type, source_doc_no, etl_batch_id
                FROM unit_revenue_fee_detail
                WHERE unit_id = :unit_id AND {date_filter}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        extras = db.execute(
            text(
                f"""
                SELECT *
                FROM revenue_extra_receipts
                WHERE unit_id = :unit_id AND {date_filter}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()

        return {
            "unit": {
                "id": int(unit.id),
                "floor_id": int(unit.floor_id),
                "unit_code": unit.unit_code,
                "status": unit.status,
            },
            "daily_summary": [
                {
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "sales_gross_profit_amount": _money(row.sales_gross_profit_amount),
                    "fee_amount": _money(row.fee_amount),
                    "extra_amount": _money(row.extra_amount),
                    "total_amount": _money(row.total_amount),
                    "sales_detail_count": int(row.sales_detail_count or 0),
                    "fee_detail_count": int(row.fee_detail_count or 0),
                    "extra_detail_count": int(row.extra_detail_count or 0),
                }
                for row in daily
            ],
            "sales_details": [
                {
                    "id": str(row.id),
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "source_group_code": row.source_group_code,
                    "source_group_name": row.source_group_name,
                    "operation_mode": row.operation_mode,
                    "supplier_code": row.supplier_code,
                    "supplier_name": row.supplier_name,
                    "contract_code": row.contract_code,
                    "sales_qty": _money(row.sales_qty),
                    "tax_excluded_sales_amount": _money(row.tax_excluded_sales_amount),
                    "tax_excluded_profit_amount": _money(row.tax_excluded_profit_amount),
                    "source_doc_no": row.source_doc_no,
                    "etl_batch_id": row.etl_batch_id,
                }
                for row in sales
            ],
            "fee_details": [
                {
                    "id": str(row.id),
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "source_group_code": row.source_group_code,
                    "source_group_name": row.source_group_name,
                    "contract_code": row.contract_code,
                    "contract_name": row.contract_name,
                    "fee_type_code": row.fee_type_code,
                    "fee_type_name": row.fee_type_name,
                    "tax_included_amount": _money(row.tax_included_amount),
                    "tax_excluded_amount": _money(row.tax_excluded_amount),
                    "source_type": row.source_type,
                    "source_doc_no": row.source_doc_no,
                    "etl_batch_id": row.etl_batch_id,
                }
                for row in fees
            ],
            "extra_receipts": [_receipt_to_dict(row) for row in extras],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取柜位收益详情失败: {exc}")


@router.get("/extra-receipts")
async def list_extra_receipts(
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    revenue_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    status_value: Optional[str] = Query(None, alias="status"),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")
    params: dict = {}
    filters: list[str] = []
    if start_date and end_date:
        filters.append("revenue_date BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date
        params["end_date"] = end_date
    elif revenue_date:
        filters.append("revenue_date = :revenue_date")
        params["revenue_date"] = revenue_date
    elif revenue_month:
        filters.append("revenue_month = :revenue_month")
        params["revenue_month"] = revenue_month
    if store_id is not None:
        filters.append("store_id = :store_id")
        params["store_id"] = store_id
    if floor_id is not None:
        filters.append("floor_id = :floor_id")
        params["floor_id"] = floor_id
    if unit_id is not None:
        filters.append("unit_id = :unit_id")
        params["unit_id"] = unit_id
    if status_value:
        filters.append("status = :status")
        params["status"] = status_value
    if keyword:
        filters.append(
            "(unit_code ILIKE :kw OR supplier_name ILIKE :kw OR contract_code ILIKE :kw OR remark ILIKE :kw)"
        )
        params["kw"] = f"%{keyword.strip()}%"
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(f"SELECT * FROM revenue_extra_receipts {where} ORDER BY revenue_date DESC, id DESC LIMIT 500"),
        params,
    ).fetchall()
    return [_receipt_to_dict(row) for row in rows]


@router.post("/extra-receipts", status_code=status.HTTP_201_CREATED)
async def create_extra_receipt(
    body: RevenueExtraReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.create")
    payload = _normalize_unit_fields(db, _model_data(body))
    if payload["amount"] == 0:
        raise HTTPException(status_code=400, detail="金额不能为 0")
    try:
        row = db.execute(
            text(
                """
                INSERT INTO revenue_extra_receipts (
                    store_id, floor_id, unit_id, unit_code, revenue_date, extra_type, amount,
                    receipt_date, voucher_no, contract_code, supplier_code, supplier_name,
                    source_group_code, source_group_name, remark, attachment_url, created_by
                )
                VALUES (
                    :store_id, :floor_id, :unit_id, :unit_code, :revenue_date, :extra_type, :amount,
                    :receipt_date, :voucher_no, :contract_code, :supplier_code, :supplier_name,
                    :source_group_code, :source_group_name, :remark, :attachment_url, :created_by
                )
                RETURNING *
                """
            ),
            {**payload, "created_by": current_user.user_id},
        ).fetchone()
        db.commit()
        return _receipt_to_dict(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建补收记录失败: {exc}")


@router.put("/extra-receipts/{receipt_id}")
async def update_extra_receipt(
    receipt_id: int,
    body: RevenueExtraReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.edit")
    current = db.execute(
        text("SELECT id, status FROM revenue_extra_receipts WHERE id = :id"),
        {"id": receipt_id},
    ).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="补收记录不存在")
    if current.status != "DRAFT":
        raise HTTPException(status_code=400, detail="只有草稿状态可以修改")

    payload = {k: v for k, v in _model_data(body).items() if v is not None}
    if "unit_id" in payload:
        payload = _normalize_unit_fields(db, payload)
    if "amount" in payload and payload["amount"] == 0:
        raise HTTPException(status_code=400, detail="金额不能为 0")
    if not payload:
        raise HTTPException(status_code=400, detail="没有可更新字段")

    allowed = {
        "store_id",
        "floor_id",
        "unit_id",
        "unit_code",
        "revenue_date",
        "extra_type",
        "amount",
        "receipt_date",
        "voucher_no",
        "contract_code",
        "supplier_code",
        "supplier_name",
        "source_group_code",
        "source_group_name",
        "remark",
        "attachment_url",
    }
    sets = [f"{key} = :{key}" for key in payload if key in allowed]
    payload["id"] = receipt_id
    try:
        row = db.execute(
            text(
                f"""
                UPDATE revenue_extra_receipts
                SET {", ".join(sets)}, updated_at = NOW()
                WHERE id = :id
                RETURNING *
                """
            ),
            payload,
        ).fetchone()
        db.commit()
        return _receipt_to_dict(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新补收记录失败: {exc}")


@router.post("/extra-receipts/{receipt_id}/confirm")
async def confirm_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.confirm")
    row = db.execute(
        text(
            """
            UPDATE revenue_extra_receipts
            SET status = 'CONFIRMED', confirmed_by = :user_id, confirmed_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status = 'DRAFT'
            RETURNING *
            """
        ),
        {"id": receipt_id, "user_id": current_user.user_id},
    ).fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=400, detail="只有草稿状态可以确认，或记录不存在")
    db.commit()
    return _receipt_to_dict(row)


@router.post("/extra-receipts/{receipt_id}/void")
async def void_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.void")
    row = db.execute(
        text(
            """
            UPDATE revenue_extra_receipts
            SET status = 'VOID', voided_by = :user_id, voided_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status <> 'VOID'
            RETURNING *
            """
        ),
        {"id": receipt_id, "user_id": current_user.user_id},
    ).fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=400, detail="记录不存在或已作废")
    db.commit()
    return _receipt_to_dict(row)


@router.post("/recalculate")
async def recalculate_revenue(
    body: RevenueRecalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.recalculate")
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    params = {"start_date": body.start_date, "end_date": body.end_date, "unit_id": body.unit_id}
    unit_filter = "AND unit_id = :unit_id" if body.unit_id is not None else ""
    try:
        db.execute(
            text(
                """
                DELETE FROM unit_revenue_sales_detail
                WHERE revenue_date BETWEEN :start_date AND :end_date
                  AND (:unit_id IS NULL OR unit_id = :unit_id)
                """
            ),
            params,
        )
        sales_result = db.execute(
            text(
                """
                WITH sales_by_group AS (
                    SELECT
                      s.sgldate::date AS revenue_date,
                      NULLIF(TRIM(s.sglmarket), '') AS store_code,
                      NULLIF(TRIM(s.sglmfid), '') AS source_group_code,
                      COALESCE(SUM(s.sglsl), 0)::numeric(18,4) AS sales_qty,
                      COALESCE(SUM(s.sglxssr), 0)::numeric(18,2) AS sales_amount,
                      COALESCE(SUM(s.sgln2), 0)::numeric(18,2) AS gross_profit_amount,
                      COUNT(*)::integer AS source_count,
                      MIN(s.sglbillno::varchar) AS first_bill_no
                    FROM salegoodslist s
                    WHERE s.sgldate BETWEEN :start_date AND :end_date
                      AND NULLIF(TRIM(s.sglmfid), '') IS NOT NULL
                    GROUP BY s.sgldate, NULLIF(TRIM(s.sglmarket), ''), NULLIF(TRIM(s.sglmfid), '')
                ),
                matched AS (
                    SELECT
                      CASE WHEN sales_by_group.store_code ~ '^[0-9]+$' THEN sales_by_group.store_code::integer ELSE NULL END AS store_id,
                      bu.floor_id,
                      bu.id AS unit_id,
                      bu.unit_code,
                      sales_by_group.revenue_date,
                      sales_by_group.source_group_code,
                      cg.group_name AS source_group_name,
                      cg.department_code,
                      cg.department_name,
                      cg.area_name,
                      f.name AS floor_name,
                      COALESCE(NULLIF(cg.operation_method, ''), binding.business_type) AS operation_mode,
                      binding.supplier_id AS supplier_code,
                      binding.brand_id AS supplier_name,
                      binding.contract_id AS contract_code,
                      sales_by_group.sales_qty,
                      sales_by_group.sales_amount,
                      sales_by_group.gross_profit_amount,
                      sales_by_group.first_bill_no,
                      sales_by_group.source_count
                    FROM sales_by_group
                    JOIN counter_groups cg
                      ON UPPER(TRIM(cg.group_code)) = UPPER(TRIM(sales_by_group.source_group_code))
                    JOIN LATERAL (
                        SELECT b.*
                        FROM business_unit_binding b
                        WHERE b.counter_group_id = cg.group_id
                          AND COALESCE(b.status, 'ACTIVE') = 'ACTIVE'
                          AND (b.start_date IS NULL OR b.start_date <= sales_by_group.revenue_date)
                          AND (b.end_date IS NULL OR b.end_date >= sales_by_group.revenue_date)
                        ORDER BY COALESCE(b.is_primary, false) DESC, b.id ASC
                        LIMIT 1
                    ) binding ON true
                    JOIN business_units bu ON bu.id = binding.shop_unit_id
                    LEFT JOIN floors f ON f.id = bu.floor_id
                    WHERE (:unit_id IS NULL OR bu.id = :unit_id)
                )
                INSERT INTO unit_revenue_sales_detail (
                    id, store_id, floor_id, unit_id, unit_code, revenue_date,
                    source_group_code, source_group_name, department_code, department_name,
                    area_name, floor_name, operation_mode, supplier_code, supplier_name,
                    contract_code, sales_qty, tax_excluded_sales_amount,
                    tax_excluded_profit_amount, source_doc_no, source_row_key,
                    etl_batch_id, raw_payload, updated_at
                )
                SELECT
                    md5(
                        matched.revenue_date::text || '|' ||
                        matched.source_group_code || '|' ||
                        matched.unit_id::text
                    ) AS id,
                    matched.store_id,
                    matched.floor_id,
                    matched.unit_id,
                    matched.unit_code,
                    matched.revenue_date,
                    matched.source_group_code,
                    matched.source_group_name,
                    matched.department_code,
                    matched.department_name,
                    matched.area_name,
                    matched.floor_name,
                    matched.operation_mode,
                    matched.supplier_code,
                    matched.supplier_name,
                    matched.contract_code,
                    matched.sales_qty,
                    matched.sales_amount,
                    matched.gross_profit_amount,
                    matched.first_bill_no,
                    matched.revenue_date::text || '_' || matched.source_group_code,
                    'RECALC_SALES_' || to_char(NOW(), 'YYYYMMDDHH24MISS'),
                    jsonb_build_object('source', 'salegoodslist', 'source_count', matched.source_count),
                    NOW()
                FROM matched
                WHERE matched.unit_id IS NOT NULL
                RETURNING id
                """
            ),
            params,
        )
        sales_detail_rows = len(sales_result.fetchall())

        db.execute(
            text(
                f"""
                DELETE FROM unit_daily_revenue_summary
                WHERE revenue_date BETWEEN :start_date AND :end_date
                  {unit_filter}
                """
            ),
            params,
        )
        result = db.execute(
            text(
                f"""
                WITH source_rows AS (
                    SELECT
                      store_id, floor_id, unit_id, unit_code, revenue_date,
                      tax_excluded_profit_amount AS sales_amount,
                      0::numeric AS fee_amount,
                      0::numeric AS extra_amount,
                      1 AS sales_count,
                      0 AS fee_count,
                      0 AS extra_count,
                      etl_batch_id
                    FROM unit_revenue_sales_detail
                    WHERE revenue_date BETWEEN :start_date AND :end_date
                      AND unit_id IS NOT NULL
                      {unit_filter}
                    UNION ALL
                    SELECT
                      store_id, floor_id, unit_id, unit_code, revenue_date,
                      0::numeric,
                      tax_excluded_amount,
                      0::numeric,
                      0,
                      1,
                      0,
                      etl_batch_id
                    FROM unit_revenue_fee_detail
                    WHERE revenue_date BETWEEN :start_date AND :end_date
                      AND unit_id IS NOT NULL
                      {unit_filter}
                    UNION ALL
                    SELECT
                      store_id, floor_id, unit_id, unit_code, revenue_date,
                      0::numeric,
                      0::numeric,
                      amount,
                      0,
                      0,
                      1,
                      NULL::varchar
                    FROM revenue_extra_receipts
                    WHERE revenue_date BETWEEN :start_date AND :end_date
                      AND status = 'CONFIRMED'
                      AND unit_id IS NOT NULL
                      {unit_filter}
                ),
                grouped AS (
                    SELECT
                      MAX(source_rows.store_id) AS store_id,
                      COALESCE(MAX(bu.floor_id), MAX(source_rows.floor_id)) AS floor_id,
                      source_rows.unit_id,
                      COALESCE(MAX(source_rows.unit_code), MAX(bu.unit_code)) AS unit_code,
                      source_rows.revenue_date,
                      COALESCE(SUM(sales_amount), 0)::numeric(18,2) AS sales_gross_profit_amount,
                      COALESCE(SUM(fee_amount), 0)::numeric(18,2) AS fee_amount,
                      COALESCE(SUM(extra_amount), 0)::numeric(18,2) AS extra_amount,
                      COALESCE(SUM(sales_count), 0)::integer AS sales_detail_count,
                      COALESCE(SUM(fee_count), 0)::integer AS fee_detail_count,
                      COALESCE(SUM(extra_count), 0)::integer AS extra_detail_count,
                      MAX(etl_batch_id) AS etl_batch_id
                    FROM source_rows
                    LEFT JOIN business_units bu ON bu.id = source_rows.unit_id
                    GROUP BY source_rows.unit_id, source_rows.revenue_date
                )
                INSERT INTO unit_daily_revenue_summary (
                    store_id, floor_id, unit_id, unit_code, revenue_date,
                    sales_gross_profit_amount, fee_amount, extra_amount,
                    sales_detail_count, fee_detail_count, extra_detail_count,
                    etl_batch_id, calculated_at, updated_at
                )
                SELECT
                    store_id, floor_id, unit_id, unit_code, revenue_date,
                    sales_gross_profit_amount, fee_amount, extra_amount,
                    sales_detail_count, fee_detail_count, extra_detail_count,
                    etl_batch_id, NOW(), NOW()
                FROM grouped
                WHERE unit_code IS NOT NULL
                RETURNING id
                """
            ),
            params,
        )
        inserted = len(result.fetchall())
        db.commit()
        return {
            "message": "收益日汇总已重算",
            "start_date": body.start_date.isoformat(),
            "end_date": body.end_date.isoformat(),
            "unit_id": body.unit_id,
            "sales_detail_rows": sales_detail_rows,
            "summary_rows": inserted,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重算收益汇总失败: {exc}")
