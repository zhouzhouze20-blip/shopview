"""ShopView Python application package."""

import importlib
import sys


for _module_name in ("models", "schemas", "routers", "utils", "services"):
    sys.modules.setdefault(_module_name, importlib.import_module(f"{__name__}.{_module_name}"))
