import json
import sys
from os.path import exists
from typing import Dict, List, Tuple


def load_whitelist_data(path: str) -> Tuple[Dict[str, List[str]], List[str]]:
    if not exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {path}: {e}")
            sys.exit(1)

    project_whitelist = data.get("whitelist_projects", {})
    if not isinstance(project_whitelist, dict):
        print(f"Expected 'whitelist_projects' key with a dictionary value in {path}")
        sys.exit(1)

    nuget_whitelist = data.get("whitelist_nugets", [])
    if not isinstance(nuget_whitelist, list):
        print(f"Expected 'whitelist_nugets' to be a list in {path}")
        sys.exit(1)

    def _norm_list(lst):
        return [str(x).strip().lower() for x in lst]

    project_whitelist = {str(k).strip().lower(): _norm_list(v) for k, v in project_whitelist.items()}
    nuget_whitelist = _norm_list(nuget_whitelist)

    return project_whitelist, nuget_whitelist
