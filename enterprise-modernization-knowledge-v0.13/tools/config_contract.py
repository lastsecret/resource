"""Strict input validation (fail closed)."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def errors(cfg):
    from jsonschema import Draft202012Validator
    schema=json.loads((ROOT/'schemas/migration-config.schema.json').read_text())
    return sorted({'.'.join(map(str,e.absolute_path)) or '<root>' for e in Draft202012Validator(schema).iter_errors(cfg)})
