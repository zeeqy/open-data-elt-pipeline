"""Command line entry point: `uv run elt <command>`."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elt", description="Malaysian open data ELT pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="check every source is reachable and matches SOURCES.md")
    args = parser.parse_args(argv)

    if args.command == "probe":
        from open_data_elt import probe

        return probe.main()
    return 1


if __name__ == "__main__":
    sys.exit(main())
