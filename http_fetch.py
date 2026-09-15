#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Политичный HTTP-клиент для парсеров: browser-like headers, session cookies, retries.
Детектирует Cloudflare challenge (403 / cf-mitigated) и помечает хост как недоступный.
"""

from __future__ import annotations

import time
from typing import Optional, Set
from urllib.parse import urlparse

import requests

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

RSS_HEADERS = {
    **BROWSER_HEADERS,
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.8",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}

_session: Optional[requests.Session] = None
_blocked_hosts: Set[str] = set()


def _normalize_host(host: str) -> str:
    host = (host or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(BROWSER_HEADERS)
    return _session


def is_host_blocked(url_or_host: str) -> bool:
    if not url_or_host:
        return False
    if "://" in url_or_host:
        host = _normalize_host(urlparse(url_or_host).netloc)
    else:
        host = _normalize_host(url_or_host)
    return host in _blocked_hosts


def mark_host_blocked(url_or_host: str, reason: str = "") -> None:
    if not url_or_host:
        return
    if "://" in url_or_host:
        host = _normalize_host(urlparse(url_or_host).netloc)
    else:
        host = _normalize_host(url_or_host)
    if not host or host in _blocked_hosts:
        return
    _blocked_hosts.add(host)
    suffix = f" ({reason})" if reason else ""
    print(
        f"🚫 Хост {host} помечен как недоступный{suffix}. "
        "Дальнейшие запросы к нему пропускаются (soft-skip)."
    )


def is_cloudflare_challenge(resp: requests.Response) -> bool:
    if resp is None:
        return False
    server = (resp.headers.get("server") or "").lower()
    cf_mitigated = (resp.headers.get("cf-mitigated") or "").lower()
    if resp.status_code in (403, 503) and ("cloudflare" in server or cf_mitigated == "challenge"):
        return True
    # Короткий снимок тела без загрузки огромных страниц
    try:
        snippet = (resp.text or "")[:800].lower()
    except Exception:
        snippet = ""
    if "just a moment" in snippet and "cloudflare" in snippet:
        return True
    if "cf-browser-verification" in snippet or "challenge-platform" in snippet:
        return True
    return False


def fetch_url(
    url: str,
    *,
    retries: int = 3,
    timeout: int = 25,
    headers: Optional[dict] = None,
    allow_redirects: bool = True,
    referer: Optional[str] = None,
) -> Optional[requests.Response]:
    """GET с ретраями. При Cloudflare challenge помечает хост и возвращает None."""
    if not url:
        return None
    if is_host_blocked(url):
        return None

    session = get_session()
    req_headers = dict(headers or BROWSER_HEADERS)
    if referer:
        req_headers["Referer"] = referer

    last_error = None
    for attempt in range(retries):
        try:
            resp = session.get(
                url,
                headers=req_headers,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )
            if is_cloudflare_challenge(resp):
                mark_host_blocked(url, "Cloudflare challenge / 403")
                return None
            if resp.status_code == 403:
                # Не Cloudflare, но запрет — один короткий retry, затем soft-skip хоста
                if attempt + 1 >= retries:
                    mark_host_blocked(url, f"HTTP {resp.status_code}")
                    return None
                time.sleep(1.5 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 403:
                mark_host_blocked(url, "HTTP 403")
                return None
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))

    if last_error:
        print(f"⚠️ HTTP fetch failed {url}: {last_error}")
    return None


def probe_skinnyms_availability() -> bool:
    """Один лёгкий probe главной SkinnyMS. False = недоступен (CF/WAF)."""
    if is_host_blocked("skinnyms.com"):
        return False
    resp = fetch_url(
        "https://skinnyms.com/",
        retries=1,
        timeout=15,
        referer="https://www.google.com/",
    )
    ok = resp is not None and resp.status_code == 200
    if not ok:
        mark_host_blocked("skinnyms.com", "probe failed")
        print(
            "ℹ️ SkinnyMS недоступен из этой сети (часто Cloudflare на IP датацентров "
            "GitHub Actions). Источник soft-skip; используйте RSS/другие фиды."
        )
    return ok
