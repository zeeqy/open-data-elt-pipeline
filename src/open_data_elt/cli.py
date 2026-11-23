"""Command line entry point: `uv run elt <command>`."""

import argparse
import sys

TABLES = ["ridership_headline", "fuelprice", "cpi_headline", "mcoicop", "bnm_exchange_rate"]


def _root_cause(err: BaseException) -> BaseException:
    while err.__cause__ or err.__context__:
        err = err.__cause__ or err.__context__
    return err


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # local .env (git-ignored); in Actions the secrets are env vars already
    parser = argparse.ArgumentParser(prog="elt", description="Malaysian open data ELT pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="check every source is reachable and matches SOURCES.md")
    load = sub.add_parser("load", help="extract + load sources into the raw dataset")
    load.add_argument(
        "--backfill", action="store_true", help="reload full history from the parquet bulk files"
    )
    load.add_argument("--only", nargs="+", choices=TABLES, help="load only these tables")
    transform = sub.add_parser("transform", help="dbt source freshness + dbt build")
    transform.add_argument("--skip-freshness", action="store_true")
    docs = sub.add_parser("docs", help="dbt docs generate (site in dbt/target/)")
    for p in (load, transform, docs):
        p.add_argument("--target", choices=["local", "motherduck"], default="local")
    alert = sub.add_parser("alert", help="send a Telegram failure alert")
    alert.add_argument("--step", required=True, help="name of the step that failed")
    alert.add_argument("--log", help="step log; its error lines go into the message")
    args = parser.parse_args(argv)

    if args.command == "alert":
        from pathlib import Path

        from open_data_elt import alert as al

        al.send(al.build_message(args.step, Path(args.log) if args.log else None))
        return 0  # the alert itself never fails the job; the failed step already did

    if args.command in ("transform", "docs"):
        from open_data_elt import transform as tf

        if args.command == "docs":
            return 0 if tf.dbt(["docs", "generate"], target=args.target) else 1
        return 0 if tf.build(freshness=not args.skip_freshness, target=args.target) else 1

    if args.command == "probe":
        from open_data_elt import probe

        return probe.main()

    if args.command == "load":
        from open_data_elt import pipeline

        try:
            pipe, info = pipeline.run(backfill=args.backfill, only=args.only, target=args.target)
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
