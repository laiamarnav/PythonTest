import fnmatch
from abc import ABC

from core.error_parser import parse_dotnet_error
from core.utils import resolve_whitelist_for_project, version_lt


class BaseCheck(ABC):
    """Base class for dotnet package checks."""

    check_type: str = ""

    def __init__(self, runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr):
        self.runner = runner
        self.blocked_packages = blocked_packages
        self.whitelist_projects = whitelist_projects
        self.whitelist_nugets = whitelist_nugets
        self.reporter = reporter
        self.tag_pr = tag_pr

    def run(self, csproj_path: str) -> bool:
        result = self.runner.list_packages(csproj_path, self.check_type)
        if result.returncode != 0:
            sev, msg, skip_ok = parse_dotnet_error(result.stderr, csproj_path)
            self.reporter.add(f"{sev}: {msg}")
            if result.stderr:
                self.runner.logger.error(f"[dotnet stderr]\n{result.stderr}")
            return skip_ok

        output_lines = result.stdout.splitlines()
        blocked_found = False
        whitelist_for_project = resolve_whitelist_for_project(csproj_path, self.whitelist_projects)
        allow_all = "*" in whitelist_for_project or "*" in self.whitelist_nugets

        for line in output_lines:
            if not line.strip().startswith("> "):
                continue
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            package_name = parts[1].lower()
            installed_version = parts[2]

            if "-beta" in installed_version:
                is_whitelisted_beta = (
                    any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project)
                    or any(fnmatch.fnmatch(package_name, wl) for wl in self.whitelist_nugets)
                    or allow_all
                )
                if not is_whitelisted_beta and not any(
                    x in self.tag_pr for x in ("ephemeral", "mocked", "ephemeral_mocked")
                ):
                    self.reporter.add(
                        f"ERROR: Found '-beta' package '{package_name}' do not allow it."
                    )
                    blocked_found = True
                continue

            matched_block_rule = None
            for blocked in self.blocked_packages:
                if fnmatch.fnmatch(package_name, blocked["name"]):
                    matched_block_rule = blocked
                    break

            if matched_block_rule:
                if matched_block_rule.get("min_version"):
                    if version_lt(installed_version, matched_block_rule["min_version"]):
                        is_whitelisted = (
                            any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project)
                            or any(fnmatch.fnmatch(package_name, wl) for wl in self.whitelist_nugets)
                            or allow_all
                        )
                        if is_whitelisted:
                            self.reporter.add(
                                f"WARNING: Package '{package_name}' below min_version but allowed by whitelist."
                            )
                            continue
                        self.reporter.add(
                            f"ERROR: Package '{package_name}' has version '{installed_version}' "
                            f"which is lower than the allowed '{matched_block_rule['min_version']}' in {csproj_path}."
                        )
                        blocked_found = True
                        continue

                if "all" in matched_block_rule.get("block_on", []) or self.check_type in matched_block_rule.get(
                    "block_on", []
                ):
                    is_whitelisted = (
                        any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project)
                        or any(fnmatch.fnmatch(package_name, wl) for wl in self.whitelist_nugets)
                        or allow_all
                    )
                    if is_whitelisted:
                        self.reporter.add(
                            f"WARNING: Package '{package_name}' would be blocked but is allowed by whitelist."
                        )
                        continue
                    self.reporter.add(
                        f"ERROR: Found blocked package '{package_name}' in {csproj_path}."
                    )
                    blocked_found = True
                    continue

        return not blocked_found
