from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .scanner import analyze, scan


def build_parser():
    parser = argparse.ArgumentParser(
        prog="envgrave",
        description="Scan projects for unused, missing, duplicated, or "
        "misconfigured environment variables.",
    )
    parser.add_argument(
        "--version", action="version", version=f"EnvGrave {__version__}"
    )
    parser.add_argument(
        "--debug", action="store_true", help="show full tracebacks on errors"
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-color", action="store_true", help="disable color output")
    common.add_argument("--json", action="store_true", help="machine-readable JSON output")
    common.add_argument("--quiet", action="store_true", help="minimal output for CI")
    common.add_argument("--strict", action="store_true", help="treat warnings as failures")
    common.add_argument(
        "--ignore", default="", help="extra directory names to ignore, comma-separated"
    )

    sub = parser.add_subparsers(dest="command")
    scan_p = sub.add_parser(
        "scan", parents=[common], help="scan a project for environment variable issues"
    )
    scan_p.add_argument("path", default=".", nargs="?", help="directory to scan")
    sub.add_parser(
        "check", parents=[common], help="scan the current directory and fail if variables are missing"
    )
    sub.add_parser(
        "list", parents=[common], help="list discovered environment variables and where they are referenced"
    )
    return parser


def _color(text, code, use_color):
    return f"\033[{code}m{text}\033[0m" if use_color else text


def _rel(path, root):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def _details(locations, root, use_color):
    parts = [
        f"{_color(_rel(loc.file, root), '90', use_color)}:{loc.line}" for loc in locations
    ]
    return ", ".join(parts)


def format_summary(analysis):
    return (
        f"{len(analysis.valid)} valid · {len(analysis.unused)} unused · "
        f"{len(analysis.missing)} missing · {len(analysis.duplicates)} duplicate"
    )


def format_report(result, analysis, use_color):
    root = result.root
    lines = []
    lines.append(f"EnvGrave v{__version__}")
    lines.append("")
    scanned = f"{result.files_scanned} files scanned"
    if result.skipped_files:
        scanned += f" ({result.skipped_files} skipped)"
    lines.append(f"Scanning {root}...")
    lines.append(scanned)
    lines.append("")

    if analysis.unused:
        lines.append(_color(f"Unused ({len(analysis.unused)})", "33", use_color))
        for name in sorted(analysis.unused):
            lines.append(
                f"  {name}   {_details(analysis.unused[name], root, use_color)}"
            )
        lines.append("")

    if analysis.missing:
        lines.append(_color(f"Missing ({len(analysis.missing)})", "31", use_color))
        for name in sorted(analysis.missing):
            lines.append(
                f"  {name}   {_details(analysis.missing[name], root, use_color)}"
            )
        lines.append("")

    if analysis.duplicates:
        lines.append(_color(f"Duplicates ({len(analysis.duplicates)})", "33", use_color))
        for name in sorted(analysis.duplicates):
            lines.append(
                f"  {name}   {_details(analysis.duplicates[name], root, use_color)}"
            )
        lines.append("")

    if analysis.inconsistent:
        lines.append(_color(f"Inconsistent ({len(analysis.inconsistent)})", "33", use_color))
        for a, b in analysis.inconsistent:
            lines.append(f"  {a}   similar to {b}")
        lines.append("")

    if analysis.env_file_diffs:
        lines.append(_color("Env file differences", "90", use_color))
        for diff in analysis.env_file_diffs:
            present = ", ".join(_rel(p, root) for p in diff["present"])
            missing_ = ", ".join(_rel(p, root) for p in diff["missing"])
            lines.append(
                f"  {diff['name']}   present in {present}; missing from {missing_}"
            )
        lines.append("")

    if analysis.valid:
        lines.append(_color(f"Valid ({len(analysis.valid)})", "32", use_color))
        for name in analysis.valid:
            lines.append(f"  {name}")
        lines.append("")

    lines.append("Summary")
    lines.append("  " + format_summary(analysis))
    return "\n".join(lines)


def format_list(result, analysis, use_color):
    root = result.root
    lines = []
    names = sorted(set(result.definitions) | set(result.references))
    for name in names:
        defs = result.definitions.get(name, [])
        refs = result.references.get(name, [])
        tags = []
        if name in analysis.unused:
            tags.append(_color("unused", "33", use_color))
        if name in analysis.missing:
            tags.append(_color("missing", "31", use_color))
        if name in analysis.duplicates:
            tags.append(_color("duplicate", "33", use_color))
        line = f"  {name}"
        if tags:
            line += " " + _color("(" + ", ".join(tags) + ")", "90", use_color)
        if defs:
            line += "\n    defined: " + _details(defs, root, use_color)
        if refs:
            line += "\n    referenced: " + _details(refs, root, use_color)
        lines.append(line)
    return "\n".join(lines)


def build_json(result, analysis):
    def def_entries(locations):
        return [{"file": _rel(loc.file, result.root), "line": loc.line} for loc in locations]

    def ref_entries(locations):
        return [{"file": _rel(loc.file, result.root), "line": loc.line} for loc in locations]

    return {
        "version": __version__,
        "root": result.root,
        "files_scanned": result.files_scanned,
        "skipped_files": result.skipped_files,
        "unused": [
            {"name": n, "definitions": def_entries(ds)}
            for n, ds in sorted(analysis.unused.items())
        ],
        "missing": [
            {"name": n, "references": ref_entries(rs)}
            for n, rs in sorted(analysis.missing.items())
        ],
        "duplicates": [
            {"name": n, "definitions": def_entries(ds)}
            for n, ds in sorted(analysis.duplicates.items())
        ],
        "inconsistent": [{"name": a, "similar_to": b} for a, b in analysis.inconsistent],
        "env_file_differences": [
            {
                "name": d["name"],
                "present": [_rel(p, result.root) for p in d["present"]],
                "missing": [_rel(p, result.root) for p in d["missing"]],
            }
            for d in analysis.env_file_diffs
        ],
        "valid": analysis.valid,
        "summary": {
            "valid": len(analysis.valid),
            "unused": len(analysis.unused),
            "missing": len(analysis.missing),
            "duplicates": len(analysis.duplicates),
        },
    }


def _prepare_console():
    # Use UTF-8 on Windows to avoid encoding errors with non-English paths
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def _run(args):
    command = args.command or "scan"
    path = getattr(args, "path", None) or "."

    ignored = set(
        part.strip()
        for part in (getattr(args, "ignore", "") or "").split(",")
        if part.strip()
    )

    use_color = (
        not getattr(args, "no_color", False)
        and not os.environ.get("NO_COLOR")
        and sys.stdout.isatty()
    )

    if not os.path.isdir(path):
        print(f"Error: Directory not found: {path}", file=sys.stderr)
        return 2

    if command == "check":
        path = "."

    result = scan(path, ignored_dirs=ignored)
    analysis = analyze(result)

    if getattr(args, "json", False):
        print(json.dumps(build_json(result, analysis), indent=2))
    elif command == "list":
        print(format_list(result, analysis, use_color))
    elif getattr(args, "quiet", False):
        print(format_summary(analysis))
    else:
        print(format_report(result, analysis, use_color))

    if command == "check" and analysis.missing:
        return 1
    if getattr(args, "strict", False) and (
        analysis.unused or analysis.missing or analysis.duplicates or analysis.inconsistent
    ):
        return 1
    return 0


def main(argv=None):
    _prepare_console()
    parser = build_parser()
    args = parser.parse_args(argv)

    debug = getattr(args, "debug", False)

    try:
        return _run(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        if debug:
            raise
        print(f"Error: {exc}", file=sys.stderr)
        return 1
