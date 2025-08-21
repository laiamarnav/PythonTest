import fnmatch
import os
import re
from os.path import dirname, exists, join
from typing import Dict, List


def _version_nums(v: str) -> List[int]:
    main = v.split('-', 1)[0] if v else ""
    parts = re.split(r"[._]", main) if main else []
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return nums


def version_lt(v1: str, v2: str) -> bool:
    try:
        a = _version_nums(v1)
        b = _version_nums(v2)
        L = max(len(a), len(b))
        if len(a) < L:
            a += [0] * (L - len(a))
        if len(b) < L:
            b += [0] * (L - len(b))
        return a < b
    except Exception:
        return False


def resolve_whitelist_for_project(csproj_path: str, whitelist_projects: Dict[str, List[str]]):
    project_name = os.path.basename(csproj_path)
    project_key = project_name.lower()
    project_stem = os.path.splitext(project_key)[0]

    merged = list(whitelist_projects.get(project_key, []))

    for k, allowed in whitelist_projects.items():
        if k == project_key:
            continue
        if fnmatch.fnmatch(project_key, k) or fnmatch.fnmatch(project_stem, k):
            merged.extend(allowed)

    return merged


def is_classic_web_app(csproj_path: str) -> bool:
    try:
        with open(csproj_path, encoding="utf-8", errors="ignore") as f:
            text = f.read().lower()
        return "microsoft.webapplication.targets" in text
    except Exception:
        return False


def uses_packages_config(csproj_path: str) -> bool:
    if exists(join(dirname(csproj_path), "packages.config")):
        return True
    try:
        with open(csproj_path, encoding="utf-8", errors="ignore") as f:
            txt = f.read().lower()
        return ("<packagereference" not in txt) and (
            "\\packages\\" in txt or "/packages/" in txt or "<hintpath>" in txt
        )
    except Exception:
        return False


def web_targets_present() -> bool:
    if os.name != "nt":
        return False
    candidates = [
        os.environ.get("VSToolsPath")
        and os.path.join(
            os.environ.get("VSToolsPath"),
            "WebApplications",
            "Microsoft.WebApplication.targets",
        ),
        r"C:\\BuildTools\\MSBuild\\Microsoft\\VisualStudio\\v17.0\\WebApplications\\Microsoft.WebApplication.targets",
        r"C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\MSBuild\\Microsoft\\VisualStudio\\v17.0\\WebApplications\\Microsoft.WebApplication.targets",
        r"C:\\Program Files\\Microsoft Visual Studio\\2022\\BuildTools\\MSBuild\\Microsoft\\VisualStudio\\v17.0\\WebApplications\\Microsoft.WebApplication.targets",
    ]
    for p in candidates:
        if p and exists(p):
            return True
    return False
