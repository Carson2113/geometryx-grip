"""Cached HTTP fetch layer. All sources are public-domain federal files."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

CACHE = Path(__file__).resolve().parent.parent / "cache"
CACHE.mkdir(exist_ok=True)

UA = {"User-Agent": "geometryx-grip/1.0 (research; contact@geometryx.io)"}

# Politeness: matches the established Geometryx sweep pattern (<= 2 req/sec).
_MIN_INTERVAL = 0.5
_last_call = [0.0]

MANIFEST = CACHE / "_manifest.json"


def _manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def _record(url: str, path: Path) -> None:
    m = _manifest()
    m[url] = {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True))


def get(url: str, name: str | None = None, timeout: int = 60) -> Path:
    """Download `url` once into the cache and return the local path.

    The manifest records URL -> sha256 + retrieval timestamp so every number in
    a scorecard is traceable to a specific byte-for-byte file. This is the
    provenance requirement in PROTOCOL.md section 8.
    """
    name = name or url.rsplit("/", 1)[-1]
    dest = CACHE / name
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    elapsed = time.time() - _last_call[0]
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    last_err = None
    for attempt in range(2):  # one retry, per the sweep convention
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            _last_call[0] = time.time()
            if r.status_code == 200 and r.content:
                dest.write_bytes(r.content)
                _record(url, dest)
                return dest
            last_err = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = repr(exc)
        time.sleep(1.5)
    raise RuntimeError(f"fetch failed for {url}: {last_err}")


def try_get(url: str, name: str | None = None) -> Path | None:
    try:
        return get(url, name)
    except Exception:  # noqa: BLE001
        return None
