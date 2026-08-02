import importlib.util
from pathlib import Path


DATABASE_MODULE_PATH = Path(__file__).resolve().parents[1] / "python_app" / "models" / "database.py"


def _load_database_module(monkeypatch, **env_values):
    for name, value in env_values.items():
        monkeypatch.setenv(name, str(value))
    spec = importlib.util.spec_from_file_location("shopview_database_pool_test", DATABASE_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_database_pool_uses_bounded_environment_budget(monkeypatch):
    module = _load_database_module(
        monkeypatch,
        DB_POOL_SIZE=2,
        DB_MAX_OVERFLOW=2,
        DB_POOL_TIMEOUT=15,
        DB_POOL_RECYCLE=1800,
    )
    try:
        assert module.DB_POOL_SIZE == 2
        assert module.DB_MAX_OVERFLOW == 2
        assert module.DB_POOL_TIMEOUT == 15
        assert module.DB_POOL_RECYCLE == 1800
        assert module.engine.pool.size() == 2
        assert module.engine.pool._max_overflow == 2
    finally:
        module.engine.dispose()


def test_database_pool_invalid_values_fall_back_or_clamp(monkeypatch):
    module = _load_database_module(
        monkeypatch,
        DB_POOL_SIZE="invalid",
        DB_MAX_OVERFLOW=-5,
        DB_POOL_TIMEOUT=0,
        DB_POOL_RECYCLE=1,
    )
    try:
        assert module.DB_POOL_SIZE == 2
        assert module.DB_MAX_OVERFLOW == 0
        assert module.DB_POOL_TIMEOUT == 1
        assert module.DB_POOL_RECYCLE == 30
    finally:
        module.engine.dispose()
