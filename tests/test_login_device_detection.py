from python_app.routers.system_management import _detect_login_device_type


WINDOWS_WECHAT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
    "NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) "
    "WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541b36)"
)

OPENHARMONY_WECOM_USER_AGENT = (
    "Mozilla/5.0 (linux; Android 13; Phone; OpenHarmony 6.1) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
    "Mobile MicroMessenger/7.0.1 wxwork/5.0.8"
)


def test_windows_wechat_is_detected_as_desktop():
    assert _detect_login_device_type(WINDOWS_WECHAT_USER_AGENT) == "DESKTOP"


def test_real_mobile_wecom_is_detected_as_mobile():
    assert _detect_login_device_type(OPENHARMONY_WECOM_USER_AGENT) == "MOBILE"


def test_standard_phone_and_desktop_user_agents_keep_their_device_types():
    assert _detect_login_device_type("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5)") == "MOBILE"
    assert _detect_login_device_type("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "DESKTOP"
    assert _detect_login_device_type(None) == "UNKNOWN"
