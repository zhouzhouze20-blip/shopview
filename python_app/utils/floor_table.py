from sqlalchemy import text
from sqlalchemy.orm import Session


def resolve_floor_table(db: Session) -> str:
    """Return the floor table name compatible with current DB schema.

    Prefer store_floors (new schema). Fallback to floors (legacy schema).
    """
    try:
        result = db.execute(text("SELECT to_regclass('public.store_floors')"))
        exists = result.scalar()
        return "store_floors" if exists else "floors"
    except Exception:
        # Conservative fallback for older schemas
        return "floors"
