#!/usr/bin/env python3
"""Validate repository-owned security controls without claiming edge coverage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERN = r"\b(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)"


def require(path: Path, expected: tuple[str, ...], errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")
        return
    source = path.read_text(encoding="utf-8")
    for value in expected:
        if value not in source:
            errors.append(f"{path.relative_to(ROOT)} is missing required control: {value}")


def main() -> int:
    errors: list[str] = []
    require(ROOT / "robots.txt", ("User-agent: *", "Allow: /", "Sitemap: https://originopenfoundation.org/sitemap.xml"), errors)
    require(ROOT / ".well-known" / "security.txt", ("Contact: mailto:contact@originopenfoundation.org", "Policy: https://originopenfoundation.org/SECURITY.md", "Expires:"), errors)
    require(ROOT / "SECURITY.md", ("Reporting a vulnerability", "main1"), errors)
    require(
        ROOT / "lara" / "security" / "index.js",
        ("retryAfterSeconds", "maxEntries", "concurrencyGate", "Content-Security-Policy", "X-Frame-Options"),
        errors,
    )
    require(
        ROOT / "lara" / "server.js",
        ("LARA_TRUST_PROXY", "LARA_CHAT_CONCURRENCY", "LARA_REQUEST_TIMEOUT_MS", "maxHeaderSize:8192", "Retry-After"),
        errors,
    )
    tracked = subprocess.run(["git", "ls-files", ".env", "lara/content"], cwd=ROOT, text=True, capture_output=True, check=False)
    if tracked.returncode:
        errors.append("Could not inspect tracked private configuration files.")
    elif tracked.stdout.strip():
        errors.append("Private configuration is tracked: " + ", ".join(tracked.stdout.splitlines()))

    secrets = subprocess.run(
        ["git", "grep", "-nI", "-E", SECRET_PATTERN],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if secrets.returncode == 0:
        errors.append("Potential credential material is tracked:\n" + secrets.stdout.strip())
    elif secrets.returncode not in (0, 1):
        errors.append("Could not scan tracked text for common credential patterns.")

    if errors:
        print("Security baseline validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Security baseline validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
