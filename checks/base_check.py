import fnmatch
from abc import ABC

from core.error_parser import parse_dotnet_error
from core.utils import resolve_whitelist_for_project, version_lt


class BaseCheck(ABC):

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
        project_label = csproj_path

        is_solution = csproj_path.lower().endswith(".sln")
        current_project_name = None 

        for raw in output_lines:
            line = raw.strip()

            if is_solution and line.lower().startswith("project '"):
                try:
                    start = line.index("'") + 1
                    end = line.index("'", start)
                    current_project_name = line[start:end]
                    project_label = current_project_name
                    whitelist_for_project = resolve_whitelist_for_project(f"{current_project_name}.csproj", self.whitelist_projects)
                    allow_all = "*" in whitelist_for_project or "*" in self.whitelist_nugets
                except ValueError:
                    pass
                continue

            if not line.startswith("> "):
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            package_name = parts[1].lower()
            installed_version = parts[2]

            prefix = f"[{self.check_type}][{project_label}]"

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
                        f"ERROR: {prefix} Found '-beta' package '{package_name}' do not allow it."
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
                                f"WARNING: {prefix} Package '{package_name}' below min_version but allowed by whitelist."
                            )
                            continue
                        self.reporter.add(
                            f"ERROR: {prefix} Package '{package_name}' has version '{installed_version}' "
                            f"which is lower than the allowed '{matched_block_rule['min_version']}'."
                        )
                        blocked_found = True
                        continue

                if "all" in matched_block_rule.get("block_on", []) or self.check_type in matched_block_rule.get("block_on", []):
                    is_whitelisted = (
                        any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project)
                        or any(fnmatch.fnmatch(package_name, wl) for wl in self.whitelist_nugets)
                        or allow_all
                    )
                    if is_whitelisted:
                        self.reporter.add(
                            f"WARNING: {prefix} Package '{package_name}' would be blocked but is allowed by whitelist."
                        )
                        continue
                    self.reporter.add(
                        f"ERROR: {prefix} Found blocked package '{package_name}'."
                    )
                    blocked_found = True
                    continue

        return not blocked_found
