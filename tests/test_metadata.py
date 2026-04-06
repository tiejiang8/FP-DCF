import re
from pathlib import Path

from fp_dcf import __version__


def _extract(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_repository_versions_stay_in_sync():
    repo_root = Path(__file__).resolve().parents[1]

    pyproject_version = _extract(
        r'^version = "([^"]+)"$',
        (repo_root / "pyproject.toml").read_text(encoding="utf-8"),
    )
    skill_version = _extract(
        r"^Version: `v([^`]+)`$",
        (repo_root / "SKILL.md").read_text(encoding="utf-8"),
    )

    assert __version__ == pyproject_version == skill_version
