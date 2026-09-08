from __future__ import annotations

import html
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


URL_REGEX = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_REGEX = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
DOMAIN_REGEX = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b",
    re.IGNORECASE,
)


def html_to_text(body: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normalize_indicator(ioc_type: str, value: str) -> str:
    value = value.strip().rstrip(".,;:!?)\"]}")
    if ioc_type == "ip":
        return str(ipaddress.ip_address(value))
    if ioc_type in {"email", "domain"}:
        return value.lower().rstrip(".")
    if ioc_type == "url":
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if not host:
            raise ValueError("URL has no host")
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    return value.lower()


def extract_indicators(body: str) -> tuple[str, list[dict[str, str]]]:
    text = html_to_text(body)
    candidates: dict[str, set[str]] = {
        "url": set(URL_REGEX.findall(text)),
        "email": set(EMAIL_REGEX.findall(text)),
        "ip": set(),
        "domain": set(DOMAIN_REGEX.findall(text)),
    }

    for candidate in IP_REGEX.findall(text):
        try:
            candidates["ip"].add(str(ipaddress.ip_address(candidate)))
        except ValueError:
            continue

    for url in candidates["url"]:
        host = urlsplit(url.rstrip(".,;:!?)\"]}")).hostname
        if host:
            try:
                ipaddress.ip_address(host)
            except ValueError:
                candidates["domain"].add(host)

    indicators: list[dict[str, str]] = []
    for ioc_type, values in candidates.items():
        for value in values:
            try:
                normalized = normalize_indicator(ioc_type, value)
            except ValueError:
                continue
            indicators.append(
                {"ioc_type": ioc_type, "value": value, "normalized_value": normalized}
            )

    indicators.sort(key=lambda item: (item["ioc_type"], item["normalized_value"]))
    return text, indicators


def ioc_matches_asset(
    ioc_type: str,
    normalized_value: str,
    asset_type: str,
    identifier: str,
    body_text: str = "",
) -> bool:
    asset_type = asset_type.lower().strip()
    identifier = identifier.lower().strip()
    value = normalized_value.lower().strip()
    if not identifier:
        return False

    if asset_type == "ip":
        return ioc_type == "ip" and value == identifier
    if asset_type == "email":
        return ioc_type == "email" and value == identifier
    if asset_type == "url":
        return ioc_type == "url" and value.rstrip("/") == identifier.rstrip("/")
    if asset_type == "keyword":
        return identifier in body_text.lower()
    if asset_type == "domain":
        candidate = ""
        if ioc_type == "domain":
            candidate = value
        elif ioc_type == "email" and "@" in value:
            candidate = value.rsplit("@", 1)[1]
        elif ioc_type == "url":
            candidate = (urlsplit(value).hostname or "").lower()
        return candidate == identifier or candidate.endswith(f".{identifier}")

    return value == identifier
