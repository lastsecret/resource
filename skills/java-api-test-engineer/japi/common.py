"""Shared artifact IO, safety checks, and diagnostics."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

class JapiError(Exception):
    """Actionable CLI error (never silently fall back)."""


def load_document(path):
    path = Path(path)
    if not path.is_file():
        raise JapiError(f"File not found: {path}")
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise JapiError("YAML support requires: pip install '.[yaml]' (JSON requires no dependency)") from e
        return yaml.safe_load(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise JapiError(f"Invalid JSON {path}: {e}") from e


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        path.parent.chmod(0o700) if path.parent.name not in ('', '.') else None
    # Open with user-only permissions by default; outputs may contain sensitive HTTP responses.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write('\n')


def save_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')


def load_jsonl(path):
    items = []
    with Path(path).open(encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise JapiError(f"Invalid JSONL {path}:{number}: {e}") from e
    return items


def normalize_url(url, allow_remote=False):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise JapiError('Target must be an HTTP(S) URL without credentials or fragment')
    if not allow_remote and parsed.hostname.lower() not in ('localhost', '127.0.0.1', '::1'):
        raise JapiError('Remote target requires explicit --allow-remote')
    return url.rstrip('/')


def is_placeholder(value):
    return isinstance(value, str) and bool(re.search(r'\$\{|<[^>]+>|\{\{', value))


def compact_summary(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
