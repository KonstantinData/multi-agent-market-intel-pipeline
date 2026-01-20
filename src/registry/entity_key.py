from __future__ import annotations

from typing import Optional


def normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/")[0]
    d = d.split("?")[0]
    d = d.split("#")[0]
    return d


def build_entity_key(*, domain: Optional[str] = None, name: Optional[str] = None) -> str:
    """Builds a deterministic entity key based on domain or name."""
    domain_norm = normalize_domain(domain or "")
    if domain_norm:
        return f"domain:{domain_norm}"
    name_norm = " ".join((name or "").strip().split()).lower()
    if name_norm:
        return f"name:{name_norm}"
    return "n/v"
