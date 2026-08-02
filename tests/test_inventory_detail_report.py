from io import BytesIO

from openpyxl import load_workbook

from python_app.services.inventory_detail_report import (
    build_historical_inventory_filter_sql,
    build_historical_inventory_workbook_file,
    build_inventory_movement_filter_sql,
    build_inventory_movement_workbook_file,
    build_inventory_filter_sql,
    build_inventory_workbook_file,
    historical_inventory_base_sql,
    inventory_movement_base_sql,
    inventory_base_sql,
    load_inventory_movement_filter_options,
)


def test_inventory_filters_are_parameterized_and_all_five_are_fuzzy():
    params = {}
    sql = build_inventory_filter_sql(
        {
            "supplier": "00070",
            "group": "6010101027",
            "goods_code": "01931",
            "barcode": "019318",
            "goods_name": "x%' OR 1=1 --",
        },
        params,
    )

    assert "00070" not in sql
    assert "6010101027" not in sql
    assert "01931" not in sql
    assert "019318" not in sql
    assert "OR 1=1" not in sql
    assert params["supplier_like"] == "%00070%"
    assert params["group_like"] == "%6010101027%"
    assert params["goods_code_like"] == "%01931%"
    assert params["barcode_like"] == "%019318%"
    assert params["goods_name_like"] == "%x%' OR 1=1 --%"
    assert "gs.gstkcsl > 0" in sql


def test_inventory_exact_lookup_supports_zero_stock_product_code_and_multiple_barcodes():
    params = {}
    sql = build_inventory_filter_sql(
        {
            "exact_code": " 2000020019318 ",
            "include_zero": True,
            "has_goodsbarcode": True,
        },
        params,
    )

    normalized = " ".join(sql.split()).lower()
    assert params["exact_code"] == "2000020019318"
    assert "gstkcsl > 0" not in normalized
    assert "gb.gbbarcode" in normalized
    assert "gs.gstgdid" in normalized
    assert "from goodsbarcode gc" in normalized
    assert "gc.gcgdid = gb.gbid" in normalized
    assert "gc.gcbarcode" in normalized


def test_inventory_exact_group_filter_matches_only_the_selected_group_code():
    params = {}
    sql = build_inventory_filter_sql({"exact_group": " 6010101027 "}, params)

    normalized = " ".join(sql.split()).lower()
    assert params["exact_group"] == "6010101027"
    assert "gs.gstmfid" in normalized
    assert "= upper(:exact_group)" in normalized
    assert "group_like" not in params
    assert "gs.gstkcsl > 0" in normalized


def test_inventory_sql_preserves_original_price_and_average_cost_formulas():
    sql = " ".join(inventory_base_sql("", "").split()).lower()

    assert "gmp.gmpuid = '00'" in sql
    assert "when coalesce(gs.gstkcsl, 0) = 0 then gs.gsthsjj" in sql
    assert "else gs.gstkcsuphsje / nullif(gs.gstkcsl, 0)" in sql
    assert "when gb.gbmanamode = '1' then gmp.gmpsj * gs.gstkcsl" in sql
    assert "1 - case when gmp.gmpkl = 1 then 0 else gmp.gmpkl end" in sql
    assert "join manaframe area_node on area_node.mfcode = mf.mfpcode" in sql
    assert "join manaframe floor_node on floor_node.mfcode = area_node.mfpcode" in sql


def test_historical_inventory_sql_uses_backup_date_range_and_original_aggregation():
    params = {}
    filter_sql = build_historical_inventory_filter_sql(
        {
            "start_date": "2026-07-19",
            "end_date": "2026-07-19",
            "group": "6010101027",
        },
        params,
    )
    sql = " ".join(historical_inventory_base_sql(filter_sql, "").split()).lower()

    assert params["start_date"] == "2026-07-19"
    assert params["end_date"] == "2026-07-19"
    assert params["group_like"] == "%6010101027%"
    assert "from goodsstock_bak gs" in sql
    assert "gs.gstdate >= cast(:start_date as date)" in sql
    assert "gs.gstdate < cast(:end_date as date) + interval '1 day'" in sql
    assert "coalesce(nullif(gs.gstsj, 0), gmp.gmpsj) as selling_price" in sql
    assert "sum(inventory_quantity) as inventory_quantity" in sql
    assert "selling_price * sum(inventory_quantity) as retail_amount" in sql
    assert "gs.gstkcsl > 0" not in sql


def test_inventory_movement_sql_preserves_original_debit_credit_and_adjustment_formulas():
    params = {}
    filter_sql = build_inventory_movement_filter_sql(
        {
            "start_date": "2026-07-19",
            "end_date": "2026-07-19",
            "supplier": "蓝",
            "group": "迪奥",
            "goods_code": "395",
            "goods_name": "防晒",
            "barcode": "039527",
            "subinventory": "1",
        },
        params,
    )
    sql = " ".join(inventory_movement_base_sql(filter_sql, "").split()).lower()

    assert params["start_date"] == "2026-07-19"
    assert params["end_date"] == "2026-07-19"
    assert params["supplier_like"] == "%蓝%"
    assert params["group_like"] == "%迪奥%"
    assert params["goods_code_like"] == "%395%"
    assert params["goods_name_like"] == "%防晒%"
    assert params["barcode_like"] == "%039527%"
    assert params["subinventory"] == "1"
    assert "j.jglsupid" in sql and "sb.sbcname" in sql
    assert "j.jglmfid" in sql and "mf.mfcname" in sql
    assert "j.jglgdid" in sql
    assert "gb.gbcname" in sql
    assert "gb.gbbarcode" in sql
    assert "j.jglfsdate >= cast(:start_date as date)" in sql
    assert "j.jglfsdate < cast(:end_date as date) + interval '1 day'" in sql
    assert "case when j.jgldac = 'd' then j.jglsl else 0 end as increase_quantity" in sql
    assert "case when j.jgldac = 'c' then j.jglsl else 0 end as decrease_quantity" in sql
    assert "j.jglhsjjje + j.jgln13 * case when trim(both from j.jgltran) in ('w', 'x') then 0 else 1 end" in sql
    assert "j.jglbhsjjje + j.jgln15 * case when trim(both from j.jgltran) in ('w', 'x') then 0 else 1 end" in sql
    assert "j.jglqmhscbje as balance_cost_tax_included" in sql
    assert "j.jglqmbhscbje as balance_cost_tax_excluded" in sql
    assert "when 'e' then '销售'" in sql
    assert "join goodsbase gb on gb.gbid = j.jglgdid" in sql


def test_inventory_movement_filter_options_use_dates_scope_and_fuzzy_keyword():
    class FakeMappings:
        def all(self):
            return [
                {
                    "value": "20630",
                    "label": "[20630] 浙江蓝雪食品有限公司",
                    "code": "20630",
                    "name": "浙江蓝雪食品有限公司",
                }
            ]

    class FakeResult:
        def mappings(self):
            return FakeMappings()

    class FakeSession:
        def __init__(self):
            self.sql = ""
            self.params = {}

        def execute(self, statement, params):
            self.sql = str(statement)
            self.params = params
            return FakeResult()

    db = FakeSession()
    options = load_inventory_movement_filter_options(
        db,
        field="supplier",
        query="蓝雪",
        filters={"start_date": "2026-07-21", "end_date": "2026-07-21"},
        scope_sql=" AND j.jglmarket = :scope_market",
        scope_params={"scope_market": "601"},
        limit=20,
    )

    normalized = " ".join(db.sql.split()).lower()
    assert db.params["start_date"] == "2026-07-21"
    assert db.params["end_date"] == "2026-07-21"
    assert db.params["supplier_like"] == "%蓝雪%"
    assert db.params["scope_market"] == "601"
    assert db.params["option_limit"] == 20
    assert "with movements as" in normalized
    assert "sb.sbcname" in normalized
    assert options == [
        {
            "value": "20630",
            "label": "[20630] 浙江蓝雪食品有限公司",
            "code": "20630",
            "name": "浙江蓝雪食品有限公司",
        }
    ]


def test_inventory_excel_export_keeps_codes_as_text_and_writes_totals():
    row = {
        "store_display": "[601] 常州购物中心",
        "floor_display": "[60101] 销售部门",
        "area_display": "[6010114] 中心一部(化妆)",
        "goods_code": "2001931",
        "barcode": "2000020019318",
        "brand_display": "[00310] Christian dior迪奥",
        "goods_name": "迪奥口红套-圣诞",
        "specification": "见商品",
        "supplier_display": "[00070] 路威酩轩香水化妆品(上海)有限公司",
        "operation_method": "经销",
        "group_display": "[6010101027] Christian dior迪奥厅",
        "subinventory_display": "[1] 柜台",
        "category_display": "[1002] 彩妆",
        "sample_label": "",
        "selling_price": 1500,
        "average_purchase_price_tax_included": 1170,
        "inventory_quantity": 77,
        "retail_amount": 47740,
        "inventory_purchase_amount_tax_excluded": 32953.2738,
        "inventory_purchase_amount_tax_included": 37237.2,
    }
    report = {
        "rows": [row],
        "summary": {
            "total_count": 1,
            "inventory_quantity": 77,
            "retail_amount": 47740,
            "inventory_purchase_amount_tax_excluded": 32953.2738,
            "inventory_purchase_amount_tax_included": 37237.2,
        },
    }

    output = build_inventory_workbook_file(
        report,
        filter_description="柜组=6010101027",
        scope_description="当前用户权限范围：全部",
    )
    try:
        workbook = load_workbook(BytesIO(output.read()), data_only=False)
    finally:
        output.close()

    sheet = workbook["实时库存查询"]
    assert sheet["A1"].value == "实时库存查询"
    assert sheet["E6"].value == "2001931"
    assert sheet["F6"].value == "2000020019318"
    assert sheet["F6"].data_type == "s"
    assert sheet["F6"].number_format == "@"
    assert sheet["R7"].value == 77
    assert sheet["S7"].value == 47740
    assert sheet["T7"].value == 32953.2738
    assert sheet["U7"].value == 37237.2
    assert sheet.freeze_panes == "A6"


def test_historical_inventory_excel_export_matches_history_columns_and_totals():
    row = {
        "inventory_date": "2026-07-19",
        "area_display": "[6010114] 中心一部(化妆)",
        "supplier_display": "[00070] 路威酩轩香水化妆品(上海)有限公司",
        "store_display": "[601] 常州购物中心",
        "group_display": "[6010101027] Christian dior迪奥厅",
        "subinventory_display": "[1] 柜台",
        "operation_method": "经销",
        "goods_code": "2015830",
        "barcode": "2000020158307",
        "goods_name": "迪奥烈艳蓝金唇线笔",
        "specification": "",
        "brand_display": "[00310] Christian dior迪奥",
        "category_display": "[1002] 彩妆",
        "sample_label": "",
        "selling_price": 230,
        "inventory_quantity": 5,
        "inventory_purchase_amount_tax_included": 897,
        "inventory_purchase_amount_tax_excluded": 793.8053,
        "retail_amount": 1150,
    }
    report = {
        "rows": [row],
        "summary": {
            "total_count": 1,
            "inventory_quantity": 5,
            "retail_amount": 1150,
            "inventory_purchase_amount_tax_excluded": 793.8053,
            "inventory_purchase_amount_tax_included": 897,
        },
    }

    output = build_historical_inventory_workbook_file(
        report,
        filter_description="库存开始日期=2026-07-19；库存结束日期=2026-07-19；柜组=6010101027",
        scope_description="当前用户权限范围：全部",
    )
    try:
        workbook = load_workbook(BytesIO(output.read()), data_only=False)
    finally:
        output.close()

    sheet = workbook["历史库存明细报表"]
    assert sheet["A1"].value == "历史库存明细报表"
    assert sheet["B6"].value.strftime("%Y-%m-%d") == "2026-07-19"
    assert sheet["I6"].value == "2015830"
    assert sheet["J6"].value == "2000020158307"
    assert sheet["J6"].number_format == "@"
    assert sheet["Q7"].value == 5
    assert sheet["R7"].value == 897
    assert sheet["S7"].value == 793.8053
    assert sheet["T7"].value == 1150
    assert sheet.freeze_panes == "A6"


def test_inventory_movement_excel_matches_4444_visible_columns_and_only_totals_movements():
    row = {
        "store_display": "[601] 常州购物中心",
        "group_display": "[6010101030] GIVENCHY紀梵希厅",
        "supplier_display": "[00070] 路威酩轩香水化妆品(上海)有限公司",
        "goods_name": "纪梵希黑能防晒霜",
        "goods_code": "2039527",
        "barcode": "2000020395276",
        "subinventory_display": "[1] 柜台",
        "accounting_date": "2026-07-19",
        "transaction_label": "销售",
        "purchase_price_tax_included": 936,
        "selling_price": 1200,
        "operation_method": "经销",
        "sample_label": "",
        "batch_sequence": 14976993,
        "increase_quantity": 0,
        "increase_amount_tax_included": 0,
        "increase_amount_tax_excluded": 0,
        "decrease_quantity": -1,
        "decrease_amount_tax_included": -936,
        "decrease_amount_tax_excluded": -828.3186,
        "balance_quantity": 16,
        "balance_cost_tax_included": 14976,
        "balance_cost_tax_excluded": 13253.0973,
        "memo": "13142611 2026-07-19",
        "specification": "见商品",
        "manufacturer_article_number": "",
    }
    report = {
        "rows": [row],
        "summary": {
            "total_count": 1,
            "increase_quantity": 0,
            "increase_amount_tax_included": 0,
            "increase_amount_tax_excluded": 0,
            "decrease_quantity": -1,
            "decrease_amount_tax_included": -936,
            "decrease_amount_tax_excluded": -828.3186,
        },
        "source_note": "数据来自本地 jxcgoodslist。",
    }

    output = build_inventory_movement_workbook_file(
        report,
        filter_description="发生开始日期=2026-07-19；发生结束日期=2026-07-19",
        scope_description="当前用户权限范围：全部",
    )
    try:
        workbook = load_workbook(BytesIO(output.read()), data_only=False)
    finally:
        output.close()

    sheet = workbook["商品进销存明细报表"]
    assert sheet["A1"].value == "商品进销存明细报表"
    assert sheet["P5"].value == "增"
    assert sheet["S5"].value == "减"
    assert sheet["V5"].value == "存"
    assert sheet["F7"].value == "2039527"
    assert sheet["G7"].value == "2000020395276"
    assert sheet["G7"].number_format == "@"
    assert sheet["I7"].value.strftime("%Y-%m-%d") == "2026-07-19"
    assert sheet["S7"].value == -1
    assert sheet["T7"].value == -936
    assert sheet["V7"].value == 16
    assert sheet["P8"].value == 0
    assert sheet["S8"].value == -1
    assert sheet["V8"].value is None
    assert sheet.freeze_panes == "A7"
