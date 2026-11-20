"""Fail if any tracked or staged file contains an XRPL seed or a private-key header.

Usage: python -I scripts/secret_scan.py [paths...]   (default: git ls-files + untracked)
Matches are reported by file and line only; the secret itself is never printed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

B58 = "[1-9A-HJ-NP-Za-km-z]"
PATTERNS = {
    "xrpl-seed-secp256k1": re.compile(rf"\bs{B58}{{28}}\b"),
    "xrpl-seed-ed25519": re.compile(rf"\bsEd{B58}{{25,29}}\b"),
    "private-key-header": re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
}
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".lock", ".whl"}
SKIP_NAMES = {".env"}  # git-ignored; never opened by agents


def candidate_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def scan(paths: list[Path]) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for path in paths:
        if path.name in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary file
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    hits.append((path, lineno, name))
    return hits


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] if argv else candidate_files()
    hits = scan(paths)
    for path, lineno, name in hits:
        print(f"SECRET? {path}:{lineno}: matches {name}", file=sys.stderr)
    if hits:
        print(f"secret scan FAILED: {len(hits)} hit(s)", file=sys.stderr)
        return 1
    print(f"secret scan ok ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
