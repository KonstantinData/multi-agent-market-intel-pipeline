from __future__ import annotations

import re


DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$")


def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_domain(domain: str) -> str:
    d = normalize_whitespace(domain).lower()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/")[0]
    d = d.split("?")[0]
    d = d.split("#")[0]
    return d


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain))
