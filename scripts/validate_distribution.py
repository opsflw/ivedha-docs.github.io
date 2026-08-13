#!/usr/bin/env python3
"""Validate the multi-site iVedha documentation distribution."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "docs.ivedha.cloud"
SITE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_TEXT = (
    "docs.example.com",
    "{{ branding.",
    "Opsflw managed Elastic Stack",
    "Opsflw Elastic Stack",
)


def main() -> int:
    errors: list[str] = []

    cname = ROOT / "CNAME"
    if not cname.is_file() or cname.read_text(encoding="utf-8").strip() != DOMAIN:
        errors.append(f"CNAME must contain only {DOMAIN}")

    for forbidden_root in ("versions.json", "latest"):
        if (ROOT / forbidden_root).exists():
            errors.append(f"root {forbidden_root} is forbidden")

    manifest_path = ROOT / "sites.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read sites.json: {exc}")
        manifest = {}

    if manifest.get("schema_version") != 1:
        errors.append("sites.json schema_version must be 1")

    seen: set[str] = set()
    root_html = read_text(ROOT / "index.html", errors)
    for site in manifest.get("sites", []):
        site_id = site.get("id", "")
        if not isinstance(site_id, str) or not SITE_ID.fullmatch(site_id):
            errors.append(f"invalid site id: {site_id!r}")
            continue
        if site_id in seen:
            errors.append(f"duplicate site id: {site_id}")
            continue
        seen.add(site_id)

        expected_path = f"/{site_id}/"
        expected_latest = f"{expected_path}latest/"
        if site.get("path") != expected_path:
            errors.append(f"{site_id}: path must be {expected_path}")
        if site.get("latest") != expected_latest:
            errors.append(f"{site_id}: latest must be {expected_latest}")
        if expected_path.lstrip("/") not in root_html:
            errors.append(f"{site_id}: root catalog does not link to {expected_path}")
        if site.get("name", "") not in root_html:
            errors.append(f"{site_id}: root catalog does not use the manifest name")

        prefix = ROOT / site_id
        latest = prefix / "latest"
        required = (
            prefix / "index.html",
            prefix / "versions.json",
            latest / "index.html",
            latest / "search" / "search_index.json",
            latest / "help-topics.json",
            latest / "sitemap.xml",
        )
        for path in required:
            if not path.is_file():
                errors.append(f"{site_id}: missing {path.relative_to(ROOT)}")

        canonical = f"https://{DOMAIN}/{site_id}/latest/"
        latest_html = read_text(latest / "index.html", errors)
        if f'<link rel="canonical" href="{canonical}">' not in latest_html:
            errors.append(f"{site_id}: latest home canonical must be {canonical}")
        validate_sitemap(latest / "sitemap.xml", canonical, errors)

    allowed_directories = {".git", ".github", "assets", "scripts", *seen}
    for path in ROOT.iterdir():
        if path.is_dir() and path.name not in allowed_directories:
            errors.append(f"unregistered top-level directory: {path.name}")

    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            errors.append(f"symbolic links are not supported: {path.relative_to(ROOT)}")
        if path.is_file() and path.suffix in {".html", ".xml", ".json", ".md"}:
            text = read_text(path, errors)
            for forbidden in FORBIDDEN_TEXT:
                if forbidden in text:
                    errors.append(
                        f"{path.relative_to(ROOT)} contains forbidden text "
                        f"{forbidden!r}"
                    )
            if path.suffix == ".html":
                validate_local_links(path, text, errors)

    for required_root in (".nojekyll", "404.html", "index.html", "assets/hub.css"):
        if not (ROOT / required_root).is_file():
            errors.append(f"missing root file: {required_root}")

    if errors:
        print("Distribution validation failed:")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1

    print(f"Distribution validation passed for {len(seen)} site(s).")
    return 0


def validate_sitemap(path: Path, prefix: str, errors: list[str]) -> None:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return
    locations = [
        element.text or ""
        for element in root.iter()
        if element.tag.endswith("loc")
    ]
    if not locations:
        errors.append(f"{path.relative_to(ROOT)} has no sitemap locations")
    for location in locations:
        if not location.startswith(prefix):
            errors.append(
                f"{path.relative_to(ROOT)} has out-of-prefix location {location}"
            )


def validate_local_links(path: Path, text: str, errors: list[str]) -> None:
    parser = LinkParser()
    parser.feed(text)
    for target in parser.targets:
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or target.startswith(("#", "mailto:", "data:")):
            continue
        raw_path = unquote(parts.path)
        if not raw_path:
            continue
        if raw_path.startswith("/"):
            resolved = ROOT / raw_path.lstrip("/")
        else:
            resolved = path.parent / raw_path
        resolved = resolved.resolve()
        if raw_path.endswith("/") or resolved.is_dir():
            resolved /= "index.html"
        if ROOT.resolve() not in resolved.parents and resolved != ROOT.resolve():
            errors.append(f"{path.relative_to(ROOT)} link leaves distribution: {target}")
        elif not resolved.is_file():
            errors.append(f"{path.relative_to(ROOT)} has broken local link {target}")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attribute = "href" if tag in {"a", "link"} else "src"
        if tag not in {"a", "link", "script", "img", "source"}:
            return
        for key, value in attrs:
            if key == attribute and value:
                self.targets.add(value)


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


if __name__ == "__main__":
    sys.exit(main())
