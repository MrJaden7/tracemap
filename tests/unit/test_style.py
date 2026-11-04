"""Project style rules that apply to every committed text file."""

import subprocess

from tracemap.config import REPO_ROOT

EM_DASH = chr(0x2014)
TEXT_SUFFIXES = {".md", ".py", ".sql", ".yml", ".yaml", ".toml", ".txt", ".env", ".j2", ".R"}


def tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for name in out.splitlines():
        path = REPO_ROOT / name
        if path.suffix in TEXT_SUFFIXES and path.is_file():
            yield path


def test_no_em_dashes():
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in tracked_text_files()
        if EM_DASH in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == [], f"Em dashes found in: {offenders}"
