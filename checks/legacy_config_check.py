import fnmatch
import xml.etree.ElementTree as ET
from os.path import dirname, exists, join

from core.utils import resolve_whitelist_for_project, version_lt


def check_packages_config(csproj_path, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
    pkg_path = join(dirname(csproj_path), "packages.config")
    if not exists(pkg_path):
        return True

    tree = ET.parse(pkg_path)
    root = tree.getroot()
    whitelist = resolve_whitelist_for_project(csproj_path, whitelist_projects)
    allow_all = "*" in whitelist or "*" in whitelist_nugets

    ok = True
    for pkg in root.findall("package"):
        name = pkg.get("id", "").lower()
        version = pkg.get("version", "")

        for b in blocked_packages:
            if fnmatch.fnmatch(name, b["name"]):
                if b.get("min_version") and version_lt(version, b["min_version"]):
                    if not allow_all:
                        ok = False
    return ok
