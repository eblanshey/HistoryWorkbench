# File responsibility: Update project metadata and dependency lock for a release.

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import subprocess


def _update_package_metadata(version: str, release_date: datetime.date) -> None:
    package_path = pathlib.Path("package.xml")
    package = package_path.read_text(encoding="utf-8")
    package, version_count = re.subn(
        r"(<version>)[^<]*(</version>)",
        rf"\g<1>{version}\g<2>",
        package,
        count=1,
    )
    package, date_count = re.subn(
        r"(<date>)[^<]*(</date>)",
        rf"\g<1>{release_date.isoformat()}\g<2>",
        package,
        count=1,
    )
    if version_count != 1 or date_count != 1:
        raise RuntimeError("package.xml must contain one version and date element")
    package_path.write_text(package, encoding="utf-8")


def _run_uv(*arguments: str) -> None:
    subprocess.run(["uv", *arguments], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update package.xml, pyproject.toml, and uv.lock for a release.")
    parser.add_argument("version", help="Release version, optionally prefixed with 'v'")
    arguments = parser.parse_args()
    if not arguments.version:
        parser.error("version must not be empty")
    version = arguments.version.removeprefix("v")

    _run_uv("version", "--dry-run", version)
    _update_package_metadata(version, datetime.date.today())
    _run_uv("version", "--frozen", version)
    _run_uv("lock")


if __name__ == "__main__":
    main()
