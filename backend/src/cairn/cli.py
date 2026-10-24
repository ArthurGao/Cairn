"""`cairn` command line (design §9.3): the core library for any tool or git hook."""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cairn import temporal
from cairn.core.context import build_context
from cairn.core.index import index_current
from cairn.core.lint import has_errors, lint_home
from cairn.core.usage import load_usage
from cairn.core.writer import sync_index, undo
from cairn.errors import CairnError
from cairn.schedule import ensure_schedule
from cairn.settings import Settings


def _settings(home: Path) -> Settings:
    return Settings(home=home)


def _lint(args: argparse.Namespace) -> int:
    settings = _settings(args.home)
    today: date = args.today or datetime.now(ZoneInfo(settings.tz)).date()
    findings = lint_home(args.home, load_usage(args.home), today, settings.lint_config())
    if args.json:
        print(json.dumps([f.model_dump() for f in findings], indent=2))
    else:
        for f in findings:
            slugs = ",".join(f.slugs) or "-"
            print(f"{f.severity:<5}  {f.check:<20}  {slugs}  {f.message}")
        print(f"{len(findings)} finding(s)")
    return 1 if has_errors(findings) else 0


def _index(args: argparse.Namespace) -> int:
    if args.check:
        current, _ = index_current(args.home)
        print("MEMORY.md is up to date" if current else "MEMORY.md is out of date")
        return 0 if current else 1
    entry = sync_index(args.home, "cli", datetime.now(UTC))
    print("MEMORY.md regenerated" if entry else "MEMORY.md is up to date")
    return 0


def _context(args: argparse.Namespace) -> int:
    settings = _settings(args.home)
    context = build_context(
        args.home, settings.l0_budget, settings.memory_index_budget, settings.skill_mounts
    )
    if args.task:
        print(f"# Task\n{args.task}\n")
    print(context.prompt)
    print(json.dumps(context.breakdown.model_dump(), indent=2))
    return 0


def _undo(args: argparse.Namespace) -> int:
    result = undo(args.home, args.change_id, "cli", datetime.now(UTC))
    for entry in result.applied:
        print(f"{entry.id}  {entry.op:<8}  {entry.slug}  (undo of {entry.undo_of})")
    if result.skipped:
        print(f"already undone: {len(result.skipped)} op(s)")
    return 0


def _schedule(_: argparse.Namespace) -> int:
    async def ensure() -> str:
        settings = Settings()
        return await ensure_schedule(await temporal.connect(settings), settings)

    print(f"cleanup schedule {asyncio.run(ensure())}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairn", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str, help: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help)
        p.add_argument("--home", type=Path, required=True, help="harness home directory")
        return p

    lint = command("lint", "check a harness home; exit 1 on any error")
    lint.add_argument("--json", action="store_true")
    lint.add_argument("--today", type=date.fromisoformat, help="YYYY-MM-DD (default: today)")
    lint.set_defaults(run=_lint)

    index = command("index", "regenerate MEMORY.md from the memory files")
    index.add_argument("--check", action="store_true", help="exit 1 on drift; write nothing")
    index.set_defaults(run=_index)

    context = command("context", "print the L0 prompt and its token breakdown")
    context.add_argument("--task", default="")
    context.set_defaults(run=_context)

    undo_cmd = command("undo", "undo a change (and its whole group)")
    undo_cmd.add_argument("change_id")
    undo_cmd.set_defaults(run=_undo)

    schedule = sub.add_parser("schedule", help="the weekly memory cleanup schedule")
    schedule.add_argument("action", choices=["ensure"], help="create or update it (idempotent)")
    schedule.set_defaults(run=_schedule)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except CairnError as exc:
        print(f"error [{exc.code}]: {exc.message}", file=sys.stderr)
        return 2


def main() -> None:
    sys.exit(run())
