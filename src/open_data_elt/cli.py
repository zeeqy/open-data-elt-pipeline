"""Command line entry point: `uv run elt <command>`."""

import argparse
import sys

TABLES = ["ridership_headline", "fuelprice", "cpi_headline", "mcoicop", "bnm_exchange_rate"]


def _root_cause(err: BaseException) -> BaseException:
    while err.__cause__ or err.__context__:
        err = err.__cause__ or err.__context__
    return err


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elt", description="Malaysian open data ELT pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="check every source is reachable and matches SOURCES.md")
    load = sub.add_parser("load", help="extract + load sources into the raw dataset")
    load.add_argument(
        "--backfill", action="store_true", help="reload full history from the parquet bulk files"
    )
    load.add_argument("--only", nargs="+", choices=TABLES, help="load only these tables")
    args = parser.parse_args(argv)

    if args.command == "probe":
        from open_data_elt import probe

        return probe.main()

    if args.command == "load":
        from open_data_elt import pipeline

        try:
            pipe, info = pipeline.run(backfill=args.backfill, only=args.only)
        except Exception as err:  # dlt wraps resource errors; show the real one
            cause = _root_cause(err)
            print(f"LOAD FAILED: {type(cause).__name__}: {cause}", file=sys.stderr)
            return 1
        print(info)
        with pipe.sql_client() as client:
            for table in args.only or TABLES:
                n = client.execute_sql(f"select count(*) from {table}")[0][0]
                print(f"  raw.{table:<20} {n:>7} rows")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
