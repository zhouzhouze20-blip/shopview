import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from python_app.routers import base_maps as api
from python_app.schemas.base_map_schemas import BaseMapCreate, BaseMapUpdate


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        session.execute(text("CREATE TABLE floors (id INTEGER PRIMARY KEY, store_code TEXT, building_code TEXT, floor_code TEXT, name TEXT)"))
        session.execute(text("INSERT INTO floors VALUES (222, '601', '601-01', '1F', '一楼'), (214, '602', '602-01', '1F', '一楼')"))
        session.execute(text("""CREATE TABLE base_maps (
            id INTEGER PRIMARY KEY, floor_id INTEGER, base_map_code TEXT UNIQUE,
            file_url TEXT, svg_viewbox TEXT, svg_width NUMERIC, svg_height NUMERIC,
            is_active BOOLEAN, created_at TIMESTAMP)"""))
        session.execute(text("CREATE UNIQUE INDEX active_floor ON base_maps(floor_id) WHERE is_active = true"))
        session.execute(text("CREATE TABLE unit_map_versions (base_map_id INTEGER)"))
        session.commit()
        monkeypatch.setattr(api, "_floor_exists", lambda db, id: (True, "floors"))
        monkeypatch.setattr(api, "_get_base_maps_floor_fk_table", lambda db: "floors")
        monkeypatch.setattr(api, "_get_table_columns", lambda db, table: {"id", "store_code", "building_code", "floor_code", "name"})
        yield session
    engine.dispose()


def create(db, floor=222, code="601-1F-底图", url="/uploads/old.svg"):
    return asyncio.run(api.create_base_map(BaseMapCreate(
        floor_id=floor, base_map_code=code, file_url=url, is_active=True,
    ), db=db))


def test_delete_then_reupload_same_code(db):
    old = create(db)
    asyncio.run(api.delete_base_map(old["id"], db=db))
    new = create(db, url="/uploads/new.svg")
    assert new["base_map_code"] == old["base_map_code"]
    assert new["file_url"] == "/uploads/new.svg"
    assert db.execute(text("SELECT count(*) FROM base_maps")).scalar() == 1


def test_other_store_conflict_explains_hidden_record_and_keeps_original(db):
    create(db)
    with pytest.raises(HTTPException) as error:
        create(db, floor=214)
    assert error.value.status_code == 400
    assert "601-01 / 1F / 一楼" in error.value.detail
    assert "所有门店、楼层中必须唯一" in error.value.detail
    assert "筛选范围" in error.value.detail
    assert db.execute(text("SELECT file_url FROM base_maps")).scalar() == "/uploads/old.svg"
    assert create(db, floor=214, code="602-1F-底图")["floor_id"] == 214


def test_edit_conflict_also_explains_location(db):
    create(db)
    other = create(db, floor=214, code="602-1F-底图")
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.update_base_map(other["id"], BaseMapUpdate(base_map_code="601-1F-底图"), db=db))
    assert "门店 601" in error.value.detail


def test_referenced_map_cannot_be_deleted(db):
    old = create(db)
    db.execute(text("INSERT INTO unit_map_versions VALUES (:id)"), {"id": old["id"]})
    db.commit()
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.delete_base_map(old["id"], db=db))
    assert error.value.status_code == 400
    assert db.execute(text("SELECT count(*) FROM base_maps")).scalar() == 1
