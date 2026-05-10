from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_floor_table(db: Session) -> str:
    """Return the floor table name compatible with current DB schema.

    The spatial model now uses public.floors as the single floor system.
    store_floors is kept only as a legacy migration source.
    """
    try:
        result = db.execute(text("SELECT to_regclass('public.floors')"))
        exists = result.scalar()
        return "floors" if exists else "store_floors"
    except Exception:
        return "floors"
