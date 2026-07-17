"""ShopView application version."""

from pathlib import Path
import os
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
DEFAULT_VERSION = "1.0.0"


def read_app_version() -> str:
    """Read the release version from the repository/package root."""
    version_file = PROJECT_ROOT / "VERSION"
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        if VERSION_PATTERN.fullmatch(version):
            return version

    fallback = os.getenv("APP_VERSION", DEFAULT_VERSION).strip()
    return fallback if VERSION_PATTERN.fullmatch(fallback) else DEFAULT_VERSION


APP_VERSION = read_app_version()
