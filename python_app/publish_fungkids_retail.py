"""Create dedicated tables and import the user's complete Nebula export."""
import argparse
from datetime import date
import json
from models.database import engine
from services.self_operated_sales import metadata, publish_export

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--create-tables", action="store_true")
    args = parser.parse_args()
    if args.create_tables:
        metadata.create_all(engine)
    print(json.dumps(publish_export(engine, args.file, start=args.start, end=args.end),
                     ensure_ascii=False, default=str, indent=2))
