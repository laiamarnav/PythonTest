import json
import sys
from os.path import exists
from src.logger import log


def load_blocked_packages(path):
    if not exists(path):
        log(f"File not found: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    blocked = data.get("blocked_packages")
    if not isinstance(blocked, list):
        log(f"Invalid JSON format: missing or invalid 'blocked_packages' list in {path}")
        sys.exit(1)

    result = []
    for entry in blocked:
        if isinstance(entry, str):
            result.append({
                "name": entry.lower(),
                "block_on": ["all"],
                "min_version": None
            })
        elif isinstance(entry, dict) and "name" in entry:
            result.append({
                "name": entry["name"].lower(),
                "block_on": entry.get("block_on", ["all"]),
                "min_version": entry.get("min_version")
            })
        else:
            log(f"Invalid blocked package entry: {entry}")
            sys.exit(1)
    return result
