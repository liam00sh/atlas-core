"""Escáner local de privacidad y secretos que nunca imprime valores."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKLIST_PATH = ROOT / "privacy_blocklist.txt"
TEXT_LIMIT = 8 * 1024 * 1024
ALLOWED_MARKER = "privacy-scan: allow"

BLOCKED_PATHS = (
    re.compile(r"(^|/)\.env($|\.)", re.I),
    re.compile(r"(^|/)(credentials?|secrets?|tokens?|client_secret)[^/]*$", re.I),
    re.compile(r"(^|/)(data/private|data/users|identity/data|memory/data/legacy)(/|$)", re.I),
    re.compile(r"(^|/)(logs?|sessions?|backups?|releases?)(/|$)", re.I),
    re.compile(r"\.(pem|key|p12|pfx|zip|rar|7z|tar|gz)$", re.I),
)

SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "telegram-token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "assigned-secret": re.compile(
        r"(?i)\b(?:api[_-]?key|token|password|passwd|secret|client[_-]?secret)\b"
        r"\s*[:=]\s*['\"]([A-Za-z0-9_./+:-]{16,})['\"]"
    ),
}


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    line: int
    commit: str = ""


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL)


def _paths(staged: bool) -> list[str]:
    if staged:
        raw = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        raw = _git("ls-files", "-z")
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


def _blocklist() -> list[re.Pattern[str]]:
    if not BLOCKLIST_PATH.is_file():
        return []
    patterns = []
    for raw in BLOCKLIST_PATH.read_text(encoding="utf-8").splitlines():
        term = raw.strip()
        if not term or term.startswith("#"):
            continue
        # Underscores are separators for this purpose: private names embedded in
        # identifiers (for example ``test_<name>``) must still be detected.
        # Limiting the boundary to ASCII letters/digits also avoids substring
        # matches inside ordinary words such as ``summary`` or ``function``.
        patterns.append(
            re.compile(
                r"(?:(?<![A-Za-z0-9])|(?<=\\b))"
                + re.escape(term)
                + r"(?![A-Za-z0-9])",
                re.I,
            )
        )
    return patterns


def _scan_text(text: str, path: str, commit: str = "") -> list[Finding]:
    findings: list[Finding] = []
    private_terms = _blocklist()
    for number, line in enumerate(text.splitlines(), 1):
        if ALLOWED_MARKER in line:
            continue
        for category, pattern in SECRET_PATTERNS.items():
            match = pattern.search(line)
            if not match:
                continue
            value = match.group(1) if category == "assigned-secret" else match.group(0)
            if any(marker in value.casefold() for marker in ("example", "invalid", "redacted", "placeholder", "fictitious")):
                continue
            findings.append(Finding(category, path, number, commit))
        if any(pattern.search(line) for pattern in private_terms):
            findings.append(Finding("private-blocklist", path, number, commit))
    return findings


def scan_tree(staged: bool) -> list[Finding]:
    findings: list[Finding] = []
    private_terms = _blocklist()
    for relative in _paths(staged):
        normalized = relative.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in private_terms):
            findings.append(Finding("private-path", normalized, 0))
        if normalized == ".env.example":
            pass
        elif any(pattern.search(normalized) for pattern in BLOCKED_PATHS):
            findings.append(Finding("blocked-path", normalized, 0))
            continue
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > TEXT_LIMIT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        findings.extend(_scan_text(text, normalized))
    return findings


def scan_history() -> list[Finding]:
    command = [
        "git", "-C", str(ROOT), "log", "--all", "--format=commit:%H",
        "--patch", "--no-ext-diff", "--unified=0", "--text",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    assert process.stdout is not None
    findings: list[Finding] = []
    commit = ""
    path = ""
    line_number = 0
    for raw in process.stdout:
        line = raw.rstrip("\n")
        if line.startswith("commit:"):
            commit = line[7:]
            continue
        if line.startswith("+++ b/"):
            path = line[6:]
            if any(pattern.search(path) for pattern in _blocklist()):
                findings.append(Finding("private-path", path, 0, commit))
            if path != ".env.example" and any(
                pattern.search(path) for pattern in BLOCKED_PATHS
            ):
                findings.append(Finding("blocked-path", path, 0, commit))
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            line_number = int(match.group(1)) if match else 0
            continue
        if line.startswith("+") and not line.startswith("+++"):
            findings.extend(_scan_text(line[1:], path or "<patch>", commit))
            line_number += 1
    return_code = process.wait()
    if return_code:
        raise RuntimeError("No se pudo recorrer el historial Git.")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = scan_tree(args.staged)
    if args.history:
        findings.extend(scan_history())
    unique = sorted(set(findings), key=lambda item: (item.category, item.path, item.commit, item.line))
    for item in unique:
        location = f"{item.path}:{item.line}" if item.line else item.path
        suffix = f" commit={item.commit[:12]}" if item.commit else ""
        print(f"[PRIVACY] {item.category} {location}{suffix}")
    print(f"Privacy scan: {len(unique)} finding(s).")
    return 1 if unique else 0


if __name__ == "__main__":
    raise SystemExit(main())
