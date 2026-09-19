"""Validate an export, optionally stage it; no production writes by default."""
import argparse
from datetime import date
import json

from services.fungkids_retail_import import import_snapshot, parse_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--channel", default="PBCZ6001")
    parser.add_argument("--staging-db", help="明确指定时才写入暂存数据库")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()
    export = parse_export(args.file, start=args.start, end=args.end, channel=args.channel)
    summary = (import_snapshot(args.staging_db, export, allow_empty=args.allow_empty)
               if args.staging_db else export.summary())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
