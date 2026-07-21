from python_app.services.wecom_client import build_js_sdk_signature


def test_build_js_sdk_signature_uses_wecom_canonical_order():
    signature = build_js_sdk_signature(
        "ticket-value",
        nonce_str="nonce-value",
        timestamp=1710000000,
        url="https://shopview.example.com/mobile/inventory?from=work#ignored",
    )

    assert signature == "9228814b5869d21ff56f274f1df8c46191d622cc"
