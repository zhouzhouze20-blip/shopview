from calendar import monthrange
from datetime import date


BIRTHDAY_COUPON_STORE_CODE = "601"
BIRTHDAY_COUPON_TYPE = "L"
BIRTHDAY_COUPON_ISSUE_ACTION = "M"
BIRTHDAY_COUPON_EXPECTED_FACE_VALUE = 100
MAX_BIRTHDAY_COUPON_MONTHS = 24

CENTER_COUPON_PROFILES = {
    "L": {
        "fallback_name": "中心生日券",
        "expected_face_value": 100,
        "expected_issue_count_per_member": 1,
    },
    "C": {
        "fallback_name": "美妆券",
        "expected_face_value": 100,
        "expected_issue_count_per_member": 2,
    },
}


def normalize_coupon_type(value: str) -> str:
    coupon_type = (value or "").strip().upper()
    if coupon_type not in CENTER_COUPON_PROFILES:
        raise ValueError("券种仅支持 L 或 C")
    return coupon_type


def center_coupon_profile(value: str) -> dict[str, int | str]:
    return CENTER_COUPON_PROFILES[normalize_coupon_type(value)]


def normalize_month(value: str) -> str:
    text = (value or "").strip()
    if len(text) != 7 or text[4] != "-":
        raise ValueError("月份必须为 YYYY-MM")
    year_text, month_text = text.split("-", 1)
    if not year_text.isdigit() or not month_text.isdigit():
        raise ValueError("月份必须为 YYYY-MM")
    year = int(year_text)
    month = int(month_text)
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise ValueError("月份超出允许范围")
    return f"{year:04d}-{month:02d}"


def next_month_start(value: str) -> date:
    normalized = normalize_month(value)
    year = int(normalized[:4])
    month = int(normalized[5:7])
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def month_window(start_month: str, end_month: str) -> tuple[date, date, int]:
    normalized_start = normalize_month(start_month)
    normalized_end = normalize_month(end_month)
    start = date(int(normalized_start[:4]), int(normalized_start[5:7]), 1)
    end = date(int(normalized_end[:4]), int(normalized_end[5:7]), 1)
    if start > end:
        raise ValueError("开始月份不能晚于结束月份")
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    if month_count > MAX_BIRTHDAY_COUPON_MONTHS:
        raise ValueError(f"查询范围不能超过 {MAX_BIRTHDAY_COUPON_MONTHS} 个月")
    return start, next_month_start(normalized_end), month_count


def month_end(value: str) -> date:
    normalized = normalize_month(value)
    year = int(normalized[:4])
    month = int(normalized[5:7])
    return date(year, month, monthrange(year, month)[1])
