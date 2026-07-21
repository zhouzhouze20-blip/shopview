import asyncio
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from python_app.routers.auth import _decode_wecom_state, get_wecom_mobile_login_url
from python_app.services.wecom_client import WeComConfig, build_mobile_login_url


class WeComMobileLoginTests(unittest.TestCase):
    def setUp(self):
        self.config = WeComConfig(
            enabled=True,
            corp_id="ww-corp",
            agent_id="1000002",
            app_secret="secret",
            redirect_base_url="https://shop.example.com",
            frontend_base_url="https://shop.example.com",
        )

    def test_builds_silent_enterprise_wechat_oauth_url(self):
        login_url = build_mobile_login_url(self.config, state="signed-state")
        parsed = urlparse(login_url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "open.weixin.qq.com")
        self.assertEqual(parsed.path, "/connect/oauth2/authorize")
        self.assertEqual(parsed.fragment, "wechat_redirect")
        self.assertEqual(query["appid"], ["ww-corp"])
        self.assertEqual(query["agentid"], ["1000002"])
        self.assertEqual(query["scope"], ["snsapi_base"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["state"], ["signed-state"])
        self.assertEqual(query["redirect_uri"], ["https://shop.example.com/api/auth/wecom/callback"])

    def test_mobile_login_endpoint_returns_to_mobile_dashboard(self):
        with patch("python_app.routers.auth.require_wecom_config", return_value=self.config):
            response = asyncio.run(get_wecom_mobile_login_url(next="/mobile"))

        state_payload = _decode_wecom_state(response["state"])
        self.assertEqual(state_payload["next"], "/mobile")
        self.assertIn(response["state"], response["login_url"])

    def test_mobile_login_endpoint_rejects_external_next_target(self):
        with patch("python_app.routers.auth.require_wecom_config", return_value=self.config):
            response = asyncio.run(get_wecom_mobile_login_url(next="//malicious.example/path"))

        state_payload = _decode_wecom_state(response["state"])
        self.assertEqual(state_payload["next"], "/")


if __name__ == "__main__":
    unittest.main()
