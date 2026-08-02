import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.unit_map_versions import (
    _match_paths_by_geometry,
    _path_geometry_fingerprint,
)


def test_same_polygon_matches_when_start_vertex_and_direction_change():
    old = "M 0 0 L 10 0 L 10 8 L 0 8 Z"
    rotated_and_reversed = "M 10 8 L 10 0 L 0 0 L 0 8 Z"

    assert _path_geometry_fingerprint(old) == _path_geometry_fingerprint(rotated_and_reversed)


def test_same_curved_path_matches_across_number_and_whitespace_formatting():
    old = "M 1.00000,2 C 3.5 4 5 6 7 8 Z"
    reformatted = "M1 2 C3.5000,4.0 5.000 6 7.0000 8Z"

    assert _path_geometry_fingerprint(old) == _path_geometry_fingerprint(reformatted)


def test_changed_coordinate_does_not_inherit_previous_unit():
    previous = [SimpleNamespace(path_data="M 0 0 L 10 0 L 10 8 L 0 8 Z", unit_id=7)]
    incoming = [("path42", "M 0 0 L 11 0 L 11 8 L 0 8 Z")]

    assert _match_paths_by_geometry(incoming, previous) == {}


def test_unique_same_coordinate_inherits_previous_unit():
    previous_geo = SimpleNamespace(path_data="M 0 0 L 10 0 L 10 8 L 0 8 Z", unit_id=7)
    incoming = [("path99", "M 10 8 L 10 0 L 0 0 L 0 8 Z")]

    assert _match_paths_by_geometry(incoming, [previous_geo]) == {0: previous_geo}


def test_duplicate_geometry_is_left_for_manual_review():
    previous = [
        SimpleNamespace(path_data="M 0 0 L 10 0 L 10 8 L 0 8 Z", unit_id=7),
        SimpleNamespace(path_data="M 10 8 L 10 0 L 0 0 L 0 8 Z", unit_id=8),
    ]
    incoming = [("path99", "M 0 0 L 10 0 L 10 8 L 0 8 Z")]

    assert _match_paths_by_geometry(incoming, previous) == {}
