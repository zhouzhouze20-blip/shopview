import asyncio
import unittest

from fastapi import HTTPException
from starlette.routing import Match

from python_app.main import app, spa_fallback


def first_matching_route_name(path: str) -> str | None:
    scope = {
        "type": "http",
        "path": path,
        "method": "GET",
        "root_path": "",
    }
    for route in app.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "name", None)
    return None


class MobileSpaFallbackTests(unittest.TestCase):
    def test_single_segment_mobile_entry_reaches_spa_fallback(self):
        self.assertEqual(first_matching_route_name("/mobile"), "spa_fallback")

    def test_nested_mobile_entry_reaches_spa_fallback(self):
        self.assertEqual(first_matching_route_name("/mobile/sales"), "spa_fallback")

    def test_missing_wecom_verification_file_stays_not_found(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(spa_fallback("WW_verify_missing.txt"))
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
