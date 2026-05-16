"""unify spatial floor ids on floors table

Revision ID: d4c9e8f1a2b3
Revises: b7c2d9e4a6f1
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4c9e8f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c2d9e4a6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TEMP TABLE tmp_floor_id_map (
          old_floor_id BIGINT PRIMARY KEY,
          new_floor_id BIGINT NOT NULL
        ) ON COMMIT DROP;
        """
    )

    # 1) Prefer explicit store_floors.floor_dict_id, then code matching.
    op.execute(
        """
        UPDATE store_floors sf
        SET floor_dict_id = f.id
        FROM floors f
        WHERE sf.floor_dict_id IS NULL
          AND COALESCE(sf.store_id::text, '') = COALESCE(f.store_code::text, '')
          AND COALESCE(sf.building_code::text, 'DEFAULT') = COALESCE(f.building_code::text, 'DEFAULT')
          AND COALESCE(sf.floor_code::text, '') = COALESCE(f.floor_code::text, '');
        """
    )
    op.execute(
        """
        INSERT INTO floors (store_code, building_code, floor_code, name, sort_no)
        SELECT
          NULLIF(sf.store_id::text, '') AS store_code,
          COALESCE(NULLIF(sf.building_code::text, ''), 'DEFAULT') AS building_code,
          COALESCE(NULLIF(sf.floor_code::text, ''), 'SF_' || sf.id::text) AS floor_code,
          COALESCE(NULLIF(sf.name::text, ''), '楼层' || sf.id::text) AS name,
          COALESCE(sf.sort_no, 0) AS sort_no
        FROM store_floors sf
        LEFT JOIN floors f
          ON COALESCE(sf.store_id::text, '') = COALESCE(f.store_code::text, '')
         AND COALESCE(sf.building_code::text, 'DEFAULT') = COALESCE(f.building_code::text, 'DEFAULT')
         AND COALESCE(sf.floor_code::text, '') = COALESCE(f.floor_code::text, '')
        WHERE sf.floor_dict_id IS NULL
          AND f.id IS NULL
        ON CONFLICT (store_code, building_code, floor_code) DO NOTHING;
        """
    )
    op.execute(
        """
        UPDATE store_floors sf
        SET floor_dict_id = f.id
        FROM floors f
        WHERE sf.floor_dict_id IS NULL
          AND COALESCE(sf.store_id::text, '') = COALESCE(f.store_code::text, '')
          AND COALESCE(sf.building_code::text, 'DEFAULT') = COALESCE(f.building_code::text, 'DEFAULT')
          AND COALESCE(sf.floor_code::text, '') = COALESCE(f.floor_code::text, '');
        """
    )
    op.execute(
        """
        INSERT INTO tmp_floor_id_map (old_floor_id, new_floor_id)
        SELECT id, floor_dict_id
        FROM store_floors
        WHERE floor_dict_id IS NOT NULL
        ON CONFLICT (old_floor_id) DO UPDATE SET new_floor_id = EXCLUDED.new_floor_id;
        """
    )

    # 2) Preserve legacy counter/hall floor ids that no longer have store_floors rows.
    op.execute(
        """
        WITH referenced AS (
          SELECT c.floor_id::bigint AS old_floor_id, s.store_code::text AS store_code
          FROM counters c
          LEFT JOIN stores s ON s.store_id = c.store_id
          WHERE c.floor_id IS NOT NULL
          UNION
          SELECT h.floor_id::bigint AS old_floor_id, s.store_code::text AS store_code
          FROM halls h
          LEFT JOIN stores s ON s.store_id = h.store_id
          WHERE h.floor_id IS NOT NULL
          UNION
          SELECT floor_id::bigint AS old_floor_id, NULL::text AS store_code FROM base_maps WHERE floor_id IS NOT NULL
          UNION
          SELECT floor_id::bigint AS old_floor_id, NULL::text AS store_code FROM unit_map_versions WHERE floor_id IS NOT NULL
          UNION
          SELECT floor_id::bigint AS old_floor_id, NULL::text AS store_code FROM business_units WHERE floor_id IS NOT NULL
        ),
        missing AS (
          SELECT r.old_floor_id, MIN(r.store_code) AS store_code
          FROM referenced r
          LEFT JOIN tmp_floor_id_map m ON m.old_floor_id = r.old_floor_id
          LEFT JOIN floors f ON f.id = r.old_floor_id
          WHERE m.old_floor_id IS NULL
            AND f.id IS NULL
          GROUP BY r.old_floor_id
        )
        INSERT INTO floors (id, store_code, building_code, floor_code, name, sort_no)
        SELECT
          old_floor_id,
          COALESCE(store_code, 'LEGACY') AS store_code,
          'LEGACY' AS building_code,
          'FLOOR_' || old_floor_id::text AS floor_code,
          '历史楼层 ' || old_floor_id::text AS name,
          old_floor_id::integer AS sort_no
        FROM missing
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute(
        """
        WITH referenced AS (
          SELECT floor_id::bigint AS old_floor_id FROM counters WHERE floor_id IS NOT NULL
          UNION SELECT floor_id::bigint FROM halls WHERE floor_id IS NOT NULL
          UNION SELECT floor_id::bigint FROM base_maps WHERE floor_id IS NOT NULL
          UNION SELECT floor_id::bigint FROM unit_map_versions WHERE floor_id IS NOT NULL
          UNION SELECT floor_id::bigint FROM business_units WHERE floor_id IS NOT NULL
        )
        INSERT INTO tmp_floor_id_map (old_floor_id, new_floor_id)
        SELECT r.old_floor_id, r.old_floor_id
        FROM referenced r
        JOIN floors f ON f.id = r.old_floor_id
        LEFT JOIN tmp_floor_id_map m ON m.old_floor_id = r.old_floor_id
        WHERE m.old_floor_id IS NULL
        ON CONFLICT (old_floor_id) DO NOTHING;
        """
    )

    # 3) Repoint all spatial tables to public.floors.
    op.execute("ALTER TABLE base_maps DROP CONSTRAINT IF EXISTS base_maps_floor_id_fkey")
    op.execute("ALTER TABLE unit_map_versions DROP CONSTRAINT IF EXISTS unit_map_versions_floor_id_fkey")
    op.execute("ALTER TABLE business_units DROP CONSTRAINT IF EXISTS business_units_floor_id_fkey")
    op.execute("ALTER TABLE counters DROP CONSTRAINT IF EXISTS counters_floor_id_fkey")
    op.execute("ALTER TABLE halls DROP CONSTRAINT IF EXISTS halls_floor_id_fkey")
    op.execute("DROP VIEW IF EXISTS counters_with_geometry")

    for table_name in ("base_maps", "unit_map_versions", "business_units", "counters", "halls"):
        op.execute(
            f"""
            UPDATE {table_name} t
            SET floor_id = m.new_floor_id
            FROM tmp_floor_id_map m
            WHERE t.floor_id::bigint = m.old_floor_id;
            """
        )

    op.execute("ALTER TABLE counters ALTER COLUMN floor_id TYPE BIGINT USING floor_id::bigint")
    op.execute("ALTER TABLE halls ALTER COLUMN floor_id TYPE BIGINT USING floor_id::bigint")

    op.execute("ALTER TABLE base_maps ADD CONSTRAINT base_maps_floor_id_fkey FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE unit_map_versions ADD CONSTRAINT unit_map_versions_floor_id_fkey FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE business_units ADD CONSTRAINT business_units_floor_id_fkey FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE RESTRICT")
    op.execute("ALTER TABLE counters ADD CONSTRAINT counters_floor_id_fkey FOREIGN KEY (floor_id) REFERENCES floors(id)")
    op.execute("ALTER TABLE halls ADD CONSTRAINT halls_floor_id_fkey FOREIGN KEY (floor_id) REFERENCES floors(id)")
    op.execute(
        """
        CREATE OR REPLACE VIEW counters_with_geometry AS
        SELECT
          c.counter_id,
          c.store_id,
          c.floor_id,
          c.counter_code,
          c.counter_name,
          c.area,
          c.counter_type,
          c.status,
          c.monthly_rent,
          c.management_fee,
          c.deposit,
          c.is_active,
          c.group_code,
          c.facade_image_url,
          c.monthly_revenue,
          c.created_at,
          c.updated_at,
          g.geometry_id,
          g.shape_type AS geometry_shape_type,
          g.position_x AS geometry_position_x,
          g.position_y AS geometry_position_y,
          g.width AS geometry_width,
          g.height AS geometry_height,
          g.rotation,
          g.polygon_coordinates AS geometry_polygon_coordinates,
          g.center_x AS geometry_center_x,
          g.center_y AS geometry_center_y,
          g.radius,
          g.ellipse_center_x,
          g.ellipse_center_y,
          g.ellipse_radius_x,
          g.ellipse_radius_y,
          g.ellipse_rotation,
          g.bounding_box_min_x AS geometry_bounding_box_min_x,
          g.bounding_box_min_y AS geometry_bounding_box_min_y,
          g.bounding_box_max_x AS geometry_bounding_box_max_x,
          g.bounding_box_max_y AS geometry_bounding_box_max_y
        FROM counters c
        LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id;
        """
    )

    op.execute("SELECT setval(pg_get_serial_sequence('floors','id'), COALESCE((SELECT MAX(id) FROM floors), 1), true)")


def downgrade() -> None:
    op.execute("ALTER TABLE base_maps DROP CONSTRAINT IF EXISTS base_maps_floor_id_fkey")
    op.execute("ALTER TABLE unit_map_versions DROP CONSTRAINT IF EXISTS unit_map_versions_floor_id_fkey")
    op.execute("ALTER TABLE business_units DROP CONSTRAINT IF EXISTS business_units_floor_id_fkey")
    op.execute("ALTER TABLE counters DROP CONSTRAINT IF EXISTS counters_floor_id_fkey")
    op.execute("ALTER TABLE halls DROP CONSTRAINT IF EXISTS halls_floor_id_fkey")
