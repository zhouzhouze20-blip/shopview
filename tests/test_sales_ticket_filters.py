import asyncio
import inspect
import unittest
from decimal import Decimal
from unittest.mock import patch


import python_app.routers.sales as sales_router
from python_app.routers.sales import (
    TICKET_EXPORT_FETCH_LIMIT,
    _date_filter_sql,
    _department_detail_filter_sql,
    _group_level_sales_rows,
    _sales_rental_exclusion_sql,
    _sales_department_exclusion_sql,
    _ticket_product_filter_sql,
    group_tickets,
    ticket_detail,
)
from python_app.services.department_display_order import department_display_sort_key


class SalesTicketFilterTests(unittest.TestCase):
    def test_ticket_query_allows_one_extra_row_for_complete_export_detection(self):
        parameter = inspect.signature(sales_router.group_tickets).parameters["limit"]
        self.assertEqual(parameter.default.default, 100)
        self.assertTrue(any(getattr(item, "le", None) == TICKET_EXPORT_FETCH_LIMIT for item in parameter.default.metadata))

    def test_date_filter_uses_finance_accounting_date(self):
        params = {}

        filters = _date_filter_sql(params, "2026-06-29", "2026-07-02")

        self.assertIn("s.sglhsrq::date >= CAST(:start_date AS DATE)", filters)
        self.assertIn("s.sglhsrq::date <= CAST(:end_date AS DATE)", filters)
        self.assertNotIn("s.sgldate", filters)
        self.assertEqual(params, {"start_date": "2026-06-29", "end_date": "2026-07-02"})

    def test_date_filter_casts_cross_year_range_as_dates(self):
        params = {}

        filters = _date_filter_sql(params, "2025-12-01", "2026-07-09")

        self.assertIn("s.sglhsrq::date >= CAST(:start_date AS DATE)", filters)
        self.assertIn("s.sglhsrq::date <= CAST(:end_date AS DATE)", filters)
        self.assertEqual(params, {"start_date": "2025-12-01", "end_date": "2026-07-09"})

    def test_department_exclusion_is_disabled_for_excel_aligned_sales(self):
        self.assertEqual(_sales_department_exclusion_sql("cg"), "")

    def test_optional_sales_exclusions_use_rental_code_and_exact_department_names(self):
        rental_sql = _sales_rental_exclusion_sql("s", enabled=True)
        department_sql = _sales_department_exclusion_sql("cg", enabled=True)

        self.assertIn("COALESCE(s.sglwmid, '')", rental_sql)
        self.assertIn("<> '5'", rental_sql)
        self.assertIn("cg.department_name", department_sql)
        self.assertIn("'中心营运部'", department_sql)
        self.assertIn("'大楼信息'", department_sql)
        self.assertIn("'书店物业部'", department_sql)
        self.assertNotIn("半山租赁部", department_sql)

    def test_group_summary_applies_optional_exclusions_at_the_correct_query_layers(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            _group_level_sales_rows(
                object(),
                start_date="2026-07-01",
                end_date="2026-07-10",
                store_id=None,
                department_code=None,
                group_code=None,
                keyword=None,
                limit=200,
                exclude_rental=True,
                exclude_backoffice_departments=True,
            )

        sales_agg_end = captured["sql"].index("group by s.sglmarket, s.sglmfid")
        self.assertIn("coalesce(s.sglwmid, '')", captured["sql"][:sales_agg_end])
        self.assertIn("cg.department_name", captured["sql"][sales_agg_end:])
        self.assertIn("'中心营运部'", captured["sql"])

    def test_department_detail_filters_apply_both_optional_exclusions(self):
        filters = _department_detail_filter_sql(
            {},
            store_id=None,
            department_code=None,
            unassigned_department=False,
            has_counter_groups=True,
            has_stores=True,
            exclude_rental=True,
            exclude_backoffice_departments=True,
        )

        self.assertIn("COALESCE(s.sglwmid, '')", filters)
        self.assertIn("<> '5'", filters)
        self.assertIn("cg.department_name", filters)
        self.assertIn("'大楼物业'", filters)

    def test_latest_sales_accounting_date_uses_salegoodslist_hsrq(self):
        captured = {}

        def fake_fetch_mappings(_db, sql, _params):
            captured["sql"] = sql.lower()
            return [{"latest_date": "2026-07-07"}]

        with (
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_fetch_mappings", fake_fetch_mappings),
        ):
            result = sales_router._latest_sales_accounting_date(object())

        self.assertEqual(result, "2026-07-07")
        self.assertIn("max(s.sglhsrq)", captured["sql"])
        self.assertIn("from salegoodslist s", captured["sql"])

    def test_new_century_supermarket_sorts_after_seventh_and_eighth_departments(self):
        rows = [
            {"department_code": "6030104", "department_name": "新世纪九部(超市)"},
            {"department_code": "6030101", "department_name": "新世纪一部(化妆)"},
            {"department_code": "6030117", "department_name": "新世纪一部(名品)"},
            {"department_code": "6030102", "department_name": "新世纪二部"},
            {"department_code": "6030112", "department_name": "新世纪三部"},
            {"department_code": "6030113", "department_name": "新世纪四部"},
            {"department_code": "6030114", "department_name": "新世纪五部(运休)"},
            {"department_code": "6030103", "department_name": "新世纪六部(男装)"},
            {"department_code": "6030115", "department_name": "新世纪七部(家居)"},
            {"department_code": "6030106", "department_name": "新世纪八部(儿童)"},
            {"department_code": "6030116", "department_name": "新世纪十部(特业)"},
            {"department_code": "", "department_name": "新世纪营运部"},
        ]

        ordered = sorted(rows, key=department_display_sort_key)

        self.assertEqual(
            [row["department_name"] for row in ordered],
            [
                "新世纪一部(化妆)",
                "新世纪一部(名品)",
                "新世纪二部",
                "新世纪三部",
                "新世纪四部",
                "新世纪五部(运休)",
                "新世纪六部(男装)",
                "新世纪七部(家居)",
                "新世纪八部(儿童)",
                "新世纪九部(超市)",
                "新世纪十部(特业)",
                "新世纪营运部",
            ],
        )

    def test_adds_goods_barcode_and_supplier_predicates(self):
        params = {}

        filters = _ticket_product_filter_sql(
            params,
            goods_code=" 2034366 ",
            barcode=" 2000020343666 ",
            supplier_code=" 10609 ",
        )

        self.assertIn("upper(trim(COALESCE(s.sglgdid, ''))) = upper(trim(:goods_code))", filters)
        self.assertIn("upper(trim(COALESCE(s.sglbarcode, ''))) = upper(trim(:barcode))", filters)
        self.assertIn("upper(trim(COALESCE(s.sglsupid, ''))) = upper(trim(:supplier_code))", filters)
        self.assertEqual(
            params,
            {
                "goods_code": "2034366",
                "barcode": "2000020343666",
                "supplier_code": "10609",
            },
        )

    def test_ignores_blank_values(self):
        params = {}

        filters = _ticket_product_filter_sql(params, goods_code="", barcode=" ", supplier_code=None)

        self.assertEqual(filters, "")
        self.assertEqual(params, {})

    def test_group_summary_sums_priced_sales_amount(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            _group_level_sales_rows(
                object(),
                start_date="2026-07-01",
                end_date="2026-07-10",
                store_id="1",
                department_code="6010101",
                group_code=None,
                keyword=None,
                limit=200,
            )

        self.assertIn("coalesce(sum(s.sglsjje), 0) as priced_sales_amount", captured["sql"])

    def test_group_summary_uses_key_equality_for_manaframe_joins(self):
        """Keep the long-range plan anchored to manaframe's unique mfcode index."""
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            _group_level_sales_rows(
                object(),
                start_date="2024-08-19",
                end_date="2025-07-18",
                store_id=None,
                department_code=None,
                group_code=None,
                keyword=None,
                limit=None,
                unrestricted=True,
            )

        self.assertIn("on mf.mfpcode = dept.mfcode", captured["sql"])
        self.assertIn("on s.sglmfid = cg.group_code", captured["sql"])
        self.assertNotIn(
            "upper(trim(coalesce(s.sglmfid, ''))) = upper(trim(coalesce(cg.group_code, '')))",
            captured["sql"],
        )

    def test_group_summary_aggregates_sales_before_dimension_joins(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            _group_level_sales_rows(
                object(),
                start_date="2024-08-19",
                end_date="2025-07-18",
                store_id=None,
                department_code=None,
                group_code=None,
                keyword=None,
                limit=None,
                unrestricted=True,
            )

        sales_agg_position = captured["sql"].index("sales_agg as")
        manaframe_join_position = captured["sql"].index("from manaframe mf")
        self.assertLess(sales_agg_position, manaframe_join_position)
        self.assertIn("group by s.sglmarket, s.sglmfid", captured["sql"])

    def test_group_tickets_sums_priced_sales_amount_by_billno(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_configure_sales_summary_timeout", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(
                sales_router,
                "_table_exists",
                lambda _db, table: table in {"manaframe", "order_point", "salehead", "salepay"},
            ),
            patch.object(
                sales_router,
                "_column_exists",
                lambda _db, table, column: (table, column)
                in {("order_point", "point_type"), ("salehead", "djlb"), ("salehead", "rqsj")},
            ),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            group_tickets(
                "6010101035",
                start_date=None,
                end_date=None,
                goods_code=None,
                barcode=None,
                supplier_code=None,
                exclude_rental=True,
                exclude_backoffice_departments=True,
                limit=100,
                offset=0,
                db=object(),
                current_user=object(),
            )

        self.assertIn("s.sglsjje", captured["sql"])
        self.assertIn("s.sglsyjid as cash_register_no", captured["sql"])
        self.assertIn("min(cash_register_no) as cash_register_no", captured["sql"])
        self.assertIn("tr.cash_register_no", captured["sql"])
        self.assertIn("coalesce(sh.rqsj, tr.sale_datetime) as sale_datetime", captured["sql"])
        self.assertNotIn("sglchecker", captured["sql"])
        self.assertIn("coalesce(sum(sglsjje), 0) as priced_sales_amount", captured["sql"])
        self.assertIn("tr.priced_sales_amount", captured["sql"])
        self.assertIn("from salepay p", captured["sql"])
        self.assertIn("p.paycode::text, '')) = '0500'", captured["sql"])
        self.assertIn("sum(coalesce(p.je, 0))", captured["sql"])
        self.assertIn("sh.djlb::text", captured["sql"])
        self.assertIn("then -abs(coalesce(lp.lq_amount, 0))", captured["sql"])
        self.assertNotIn("sum(sglgcert)", captured["sql"])
        self.assertIn("'香奈儿活动补发'", captured["sql"])
        self.assertIn("coalesce(s.sglwmid, '')", captured["sql"])
        self.assertIn("cg.department_name", captured["sql"])

    def test_group_tickets_keeps_indexed_ticket_keys_for_enrichment_joins(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_configure_sales_summary_timeout", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(
                sales_router,
                "_table_exists",
                lambda _db, table: table in {"manaframe", "order_point", "salehead", "salepay"},
            ),
            patch.object(
                sales_router,
                "_column_exists",
                lambda _db, table, column: (table, column)
                in {("order_point", "point_type"), ("salehead", "djlb"), ("salehead", "rqsj")},
            ),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
        ):
            group_tickets(
                "6010101030",
                start_date="2025-10-29",
                end_date="2025-12-01",
                goods_code=None,
                barcode=None,
                supplier_code=None,
                exclude_rental=False,
                exclude_backoffice_departments=False,
                limit=100,
                offset=200,
                db=object(),
                current_user=object(),
            )

        sql = captured["sql"]
        self.assertIn("s.sglbillno as billno", sql)
        self.assertIn("p.billno in (select billno from ticket_rows)", sql)
        self.assertIn("left join salehead sh on sh.billno = tr.billno", sql)
        self.assertIn("order_id in (select billno::text from ticket_rows)", sql)
        self.assertIn("trim(both from tr.billno::text) as billno", sql)
        self.assertIn("limit :limit offset :offset", sql)
        self.assertEqual(captured["params"]["limit"], 100)
        self.assertEqual(captured["params"]["offset"], 200)
        self.assertNotIn("trim(both from p.billno::text)", sql)
        self.assertNotIn("sh.billno::text", sql)

    def test_group_ticket_summary_counts_all_tickets_without_page_limit(self):
        captured = {}

        def fake_fetch(_db, sql, params):
            captured["sql"] = " ".join(sql.lower().split())
            captured["params"] = params
            return [
                {
                    "group_code": "6010101030",
                    "group_name": "GIVENCHY紀梵希厅",
                    "department_code": "6010114",
                    "department_name": "中心一部(化妆)",
                    "store_id": "601",
                    "ticket_count": 201,
                    "priced_sales_amount": 268414,
                    "effective_sales": 226925.4625,
                    "net_profit": 16662.1925,
                }
            ]

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: object()),
            patch.object(sales_router, "_configure_sales_summary_timeout", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
            patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
            patch.object(sales_router, "_fetch_mappings", fake_fetch),
            patch.object(sales_router, "_row_allowed", lambda *_args, **_kwargs: True),
        ):
            result = sales_router.group_tickets_summary(
                "6010101030",
                start_date="2025-10-29",
                end_date="2025-12-01",
                goods_code=None,
                barcode=None,
                supplier_code=None,
                exclude_rental=False,
                exclude_backoffice_departments=False,
                db=object(),
                current_user=object(),
            )

        self.assertEqual(result["ticket_count"], 201)
        self.assertNotIn("limit", captured["sql"])
        self.assertNotIn("offset", captured["sql"])
        self.assertEqual(captured["params"]["group_code"], "6010101030")

    def test_ticket_detail_falls_back_to_goodsbase_name(self):
        def fake_table_exists(_db, table_name):
            return table_name in {"salehead", "salegoods", "goodsbase"}

        def fake_fetch_mappings(_db, sql, _params):
            lowered_sql = sql.lower()
            if "from salegoods" in lowered_sql and "order by g.rowno" in lowered_sql:
                name = "牛丼饭 单人定食" if "goodsbase" in lowered_sql and "gbcname" in lowered_sql else None
                return [
                    {
                        "rowno": 1,
                        "barcode": "2000020544063",
                        "code": "2054406",
                        "name": name,
                    }
                ]
            if "as group_code" in lowered_sql:
                return []
            if "from salehead" in lowered_sql:
                return [{"billno": "13030635"}]
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_table_exists", fake_table_exists),
            patch.object(sales_router, "_fetch_mappings", fake_fetch_mappings),
        ):
            result = ticket_detail("13030635", db=object(), current_user=object())

        self.assertEqual(result["goods"][0]["name"], "牛丼饭 单人定食")

    def test_ticket_detail_aliases_salegoods_when_joining_goodsbase(self):
        def fake_table_exists(_db, table_name):
            return table_name in {"salehead", "salegoods", "goodsbase"}

        captured_sql = []

        def fake_fetch_mappings(_db, sql, _params):
            lowered_sql = sql.lower()
            captured_sql.append(lowered_sql)
            if "from salegoods" in lowered_sql and "order by g.rowno" in lowered_sql:
                return []
            if "as group_code" in lowered_sql:
                return []
            if "from salehead" in lowered_sql:
                return [{"billno": "13033424"}]
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_table_exists", fake_table_exists),
            patch.object(sales_router, "_fetch_mappings", fake_fetch_mappings),
        ):
            ticket_detail("13033424", db=object(), current_user=object())

        goods_queries = [sql for sql in captured_sql if "from salegoods" in sql and "order by g.rowno" in sql]
        self.assertTrue(goods_queries)
        self.assertIn("from salegoods g", goods_queries[0])

    def test_ticket_detail_prefers_paymode_name_for_payment_display(self):
        def fake_table_exists(_db, table_name):
            return table_name in {"salehead", "salegoods", "salepay", "paymode"}

        captured_sql = []

        def fake_fetch_mappings(_db, sql, _params):
            lowered_sql = sql.lower()
            captured_sql.append(lowered_sql)
            if "as group_code" in lowered_sql:
                return []
            if "from salehead" in lowered_sql:
                return [{"billno": "13030635"}]
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "_table_exists", fake_table_exists),
            patch.object(sales_router, "_fetch_mappings", fake_fetch_mappings),
        ):
            ticket_detail("13030635", db=object(), current_user=object())

        payment_queries = [sql for sql in captured_sql if "from salepay" in sql]
        self.assertTrue(payment_queries)
        self.assertIn("left join paymode pm", payment_queries[0])
        self.assertIn("coalesce(nullif(pm.pmname, ''), nullif(p.payname, ''), p.payname) as payname", payment_queries[0])

    def test_ticket_detail_keeps_numeric_billno_indexable(self):
        captured_queries = []

        def fake_fetch_mappings(_db, sql, params):
            captured_queries.append((" ".join(sql.lower().split()), params))
            return []

        with (
            patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
            patch.object(
                sales_router,
                "_table_exists",
                lambda _db, table_name: table_name in {"salehead", "salegoods", "salepay"},
            ),
            patch.object(sales_router, "_fetch_mappings", fake_fetch_mappings),
        ):
            ticket_detail("13346167", db=object(), current_user=object())

        bill_queries = [(sql, params) for sql, params in captured_queries if ":billno" in sql]
        self.assertGreaterEqual(len(bill_queries), 4)
        for sql, params in bill_queries:
            self.assertNotIn("billno::varchar", sql)
            self.assertRegex(sql, r"(?:g\.|p\.)?billno = :billno")
            self.assertEqual(params["billno"], Decimal("13346167"))
