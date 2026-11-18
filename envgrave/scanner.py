"""EnvGrave scanner.

Scans a project directory for environment variable problems: unused,
missing, duplicated, or inconsistently named variables.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field


__all__ = ["scan", "analyze", "ScanResult", "Analysis"]

DEFAULT_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".next",
    "out",
    "__pycache__",
    ".tox",
    ".eggs",
    "target",
    "bin",
    "obj",
}

ENV_FILES = (".env", ".env.local", ".env.example", ".env.production", ".env.development")

MAX_FILE_SIZE = 1_000_000

NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

JS_DOT = re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)")
JS_BRACKET = re.compile(r'process\.env\[(["\'])([A-Za-z_][A-Za-z0-9_]*)\1\]')
JS_DESTRUCTURE = re.compile(r"\{\s*([^{}]*?)\s*\}\s*=\s*process\.env")

PY_GETENV = re.compile(r"os\.getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']")
PY_ENVIRON_GET = re.compile(r"os\.environ\.get\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']")
PY_ENVIRON_INDEX = re.compile(r"os\.environ\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]")


@dataclass
class EnvDefinition:
    name: str
    file: str
    line: int


@dataclass
class EnvReference:
    name: str
    file: str
    line: int


@dataclass
class ScanResult:
    root: str
    definitions: dict[str, list[EnvDefinition]] = field(default_factory=dict)
    references: dict[str, list[EnvReference]] = field(default_factory=dict)
    env_files: list[str] = field(default_factory=list)
    files_scanned: int = 0
    skipped_files: int = 0


@dataclass
class Analysis:
    unused: dict[str, list[EnvDefinition]]
    missing: dict[str, list[EnvReference]]
    duplicates: dict[str, list[EnvDefinition]]
    inconsistent: list[tuple[str, str]]
    env_file_diffs: list[dict]
    valid: list[str]


def _line_number(text, pos):
    return text.count("\n", 0, pos) + 1


def _read_text(path):
    """Read a file as text. Returns None for binaries or oversized files."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_FILE_SIZE + 1)
    except OSError:
        return None
    if len(data) > MAX_FILE_SIZE:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")


def _is_within(path, root):
    try:
        real = os.path.realpath(path)
        root_real = os.path.realpath(root)
    except OSError:
        return False
    return real == root_real or real.startswith(root_real + os.sep)


def parse_env_file(path):
    """Return [(name, line), ...] for assignments found in an env file."""
    entries = []
    text = _read_text(path)
    if text is None:
        return entries
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = ENV_LINE.match(line)
        if m:
            entries.append((m.group(1), lineno))
    return entries


def _add_definitions(result, path):
    for name, lineno in parse_env_file(path):
        result.definitions.setdefault(name, []).append(EnvDefinition(name, path, lineno))


def _js_references(text):
    refs = []
    for m in JS_DOT.finditer(text):
        refs.append((m.group(1), _line_number(text, m.start())))
    for m in JS_BRACKET.finditer(text):
        refs.append((m.group(2), _line_number(text, m.start())))
    for m in JS_DESTRUCTURE.finditer(text):
        for part in m.group(1).split(","):
            name = part.strip()
            name = name.split("=")[0].split(":")[0].strip()
            if NAME_RE.fullmatch(name):
                refs.append((name, _line_number(text, m.start())))
    return refs


def _py_references(text):
    refs = []
    for m in PY_GETENV.finditer(text):
        refs.append((m.group(1), _line_number(text, m.start())))
    for m in PY_ENVIRON_GET.finditer(text):
        refs.append((m.group(1), _line_number(text, m.start())))
    for m in PY_ENVIRON_INDEX.finditer(text):
        refs.append((m.group(1), _line_number(text, m.start())))
    return refs


def _scan_source_file(result, path):
    text = _read_text(path)
    if text is None:
        result.skipped_files += 1
        return
    for name, lineno in _js_references(text):
        result.references.setdefault(name, []).append(EnvReference(name, path, lineno))
    for name, lineno in _py_references(text):
        result.references.setdefault(name, []).append(EnvReference(name, path, lineno))


def _load_ignore_file(root, ignored):
    path = os.path.join(root, ".envgraveignore")
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                name = line.strip()
                if name and not name.startswith("#"):
                    ignored.add(name)
    except OSError:
        pass


def scan(root, ignored_dirs=None):
    if ignored_dirs is None:
        ignored_dirs = set()
    ignored = set(DEFAULT_IGNORED_DIRS) | set(ignored_dirs)
    root = os.path.abspath(root)
    result = ScanResult(root=root)

    _load_ignore_file(root, ignored)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ignored
            and (
                not os.path.islink(os.path.join(dirpath, d))
                or _is_within(os.path.join(dirpath, d), root)
            )
        ]
        for name in filenames:
            full = os.path.join(dirpath, name)
            if name in ignored:
                continue
            if os.path.islink(full) and not _is_within(full, root):
                continue
            if name in ENV_FILES:
                result.env_files.append(full)
                _add_definitions(result, full)
            else:
                _scan_source_file(result, full)
                result.files_scanned += 1
    return result


def analyze(result):
    defined = set(result.definitions)
    referenced = set(result.references)

    unused = {n: ds for n, ds in result.definitions.items() if n not in referenced}
    missing = {n: rs for n, rs in result.references.items() if n not in defined}
    duplicates = {}
    for name, ds in result.definitions.items():
        by_file = {}
        for d in ds:
            by_file.setdefault(d.file, []).append(d)
        dups = [d for file_ds in by_file.values() for d in file_ds if len(file_ds) > 1]
        if dups:
            duplicates[name] = dups

    names = sorted(defined)
    inconsistent = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if difflib.SequenceMatcher(None, a, b).ratio() >= 0.82:
                # suggest the shorter, simpler name first
                if len(b) < len(a) or (len(b) == len(a) and b < a):
                    a, b = b, a
                inconsistent.append((a, b))

    for name in sorted(referenced - defined):
        best = None
        best_ratio = 0.0
        for other in names:
            ratio = difflib.SequenceMatcher(None, name, other).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = other
        if best and best_ratio >= 0.82:
            inconsistent.append((name, best))

    per_file = {}
    for path in result.env_files:
        per_file[path] = {
            d.name
            for defs in result.definitions.values()
            for d in defs
            if d.file == path
        }
    env_file_diffs = []
    if len(per_file) > 1:
        all_keys = set().union(*per_file.values())
        for name in sorted(all_keys):
            present = [p for p, keys in per_file.items() if name in keys]
            if 0 < len(present) < len(per_file):
                env_file_diffs.append(
                    {
                        "name": name,
                        "present": present,
                        "missing": [p for p in per_file if p not in present],
                    }
                )

    valid = sorted(n for n in defined if n in referenced and n not in duplicates)

    return Analysis(unused, missing, duplicates, inconsistent, env_file_diffs, valid)
