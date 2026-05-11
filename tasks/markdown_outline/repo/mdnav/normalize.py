from __future__ import annotations

import posixpath
import re


def slugify(title: str) -> str:
    slug = title.strip().lower().replace(" ", "-")
    return slug


def normalize_href(href: str, base_path: str) -> str:
    if href.startswith(("http://", "https://", "mailto:")):
        return href
    base_dir = posixpath.dirname(base_path)
    return posixpath.normpath(posixpath.join(base_dir, href))
