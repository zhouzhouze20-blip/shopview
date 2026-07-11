from typing import Any


def department_display_sort_key(row: dict[str, Any]) -> tuple[int, int, str, str]:
    name = str(row.get("department_name") or "")
    code = str(row.get("department_code") or "")
    new_century_order = {
        "6030101": 1,
        "6030117": 2,
        "6030102": 3,
        "6030112": 4,
        "6030113": 5,
        "6030114": 6,
        "6030103": 7,
        "6030115": 8,
        "6030106": 9,
        "6030104": 10,
        "6030116": 11,
    }
    if code in new_century_order:
        return (0, new_century_order[code], name, code)
    if name.startswith("新世纪"):
        return (1, 999, name, code)

    if "超市" in name:
        return (2, 0, name, code)
    if "生鲜" in name:
        return (2, 1, name, code)

    cn_order = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    for cn, order in cn_order.items():
        if f"{cn}部" in name:
            return (3, order, name, code)
    return (4, 999, name, code)
