import os, fnmatch, subprocess, xml.etree.ElementTree as ET
from os.path import exists, dirname, join
from src.logger import log, log_summary
from src.parsers import (
    find_csproj_files,
    uses_packages_config,
    is_classic_web_app,
    resolve_whitelist_for_project,
    version_lt,
    parse_dotnet_error,
)

NUGET_SOURCES = [
    "https://vueling.pkgs.visualstudio.com/_packaging/vy-nuget/nuget/v3/index.json",
    "https://api.nuget.org/v3/index.json"
]


def web_targets_present() -> bool:
    if os.name != "nt":
        return False
    candidates = [
        os.environ.get("VSToolsPath") and os.path.join(os.environ.get("VSToolsPath"), "WebApplications", "Microsoft.WebApplication.targets"),
        r"C:\BuildTools\MSBuild\Microsoft\VisualStudio\v17.0\WebApplications\Microsoft.WebApplication.targets",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Microsoft\VisualStudio\v17.0\WebApplications\Microsoft.WebApplication.targets",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Microsoft\VisualStudio\v17.0\WebApplications\Microsoft.WebApplication.targets"
    ]
    for p in candidates:
        if p and exists(p):
            return True
    return False


def run_dotnet_restore(target_path: str) -> bool:
    cmd = ["dotnet", "restore", target_path]
    for source in NUGET_SOURCES:
        cmd.extend(["--source", source])

    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    log(f"\n[RESTORE] {os.path.abspath(target_path)}")
    if r.stdout:
        log(r.stdout)
    if r.returncode != 0:
        log_summary(f"ERROR: dotnet restore failed for {target_path} (code {r.returncode}).")
        if r.stderr:
            log(f"[dotnet stderr]\n{r.stderr}")
        return False
    return True


def check_packages_config(csproj_path, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
    """Analiza manualmente los projects con packages.config (legacy)"""
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
                        log_summary(f"ERROR: {name} {version} < {b['min_version']} in {csproj_path}")
                        ok = False
    return ok


def run_dotnet_package_check(csproj_path, check_type, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
    cmd = ["dotnet", "list", csproj_path, "package", f"--{check_type}", "--include-transitive"]
    for source in NUGET_SOURCES:
        cmd.extend(["--source", source])

    whitelist_for_project = resolve_whitelist_for_project(csproj_path, whitelist_projects)
    allow_all = ("*" in whitelist_for_project) or ("*" in whitelist_nugets)

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    log(f"\n [{check_type.upper()} PACKAGES] ")
    log("-" * 60)
    log(f"\nChecking packages for {os.path.abspath(csproj_path)}")

    if result.stdout:
        log(result.stdout)

    if result.returncode != 0:
        sev, msg, skip_ok = parse_dotnet_error(result.stderr, csproj_path)
        log_summary(f"{sev}: {msg}")
        if result.stderr:
            log(f"[dotnet stderr]\n{result.stderr}")
        return skip_ok

    output_lines = result.stdout.splitlines()
    blocked_found = False

    for line in output_lines:
        if not line.strip().startswith("> "):
            continue

        parts = line.strip().split()
        if len(parts) < 4:
            continue

        package_name = parts[1].lower()
        installed_version = parts[2]

        # --- Bloqueo de paquetes -beta ---
        if "-beta" in installed_version:
            is_whitelisted_beta = (
                any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project) or
                any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_nugets) or
                allow_all
            )
            if not is_whitelisted_beta and not any(x in tag_pr for x in ("ephemeral", "mocked", "ephemeral_mocked")):
                log_summary(f"ERROR: Found '-beta' package '{package_name}' do not allow it.")
                blocked_found = True
            continue

        # --- Bloqueo por reglas de blocked_packages ---
        matched_block_rule = None
        for blocked in blocked_packages:
            if fnmatch.fnmatch(package_name, blocked["name"]):
                matched_block_rule = blocked
                break

        if matched_block_rule:
            # min_version
            if matched_block_rule.get("min_version"):
                if version_lt(installed_version, matched_block_rule["min_version"]):
                    is_whitelisted = (
                        any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project) or
                        any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_nugets) or
                        allow_all
                    )
                    if not is_whitelisted:
                        log_summary(
                            f"ERROR: Package '{package_name}' has version '{installed_version}' "
                            f"which is lower than the allowed '{matched_block_rule['min_version']}' in {csproj_path}."
                        )
                        blocked_found = True
                    else:
                        log_summary(f"WARNING: Package '{package_name}' below min_version but allowed by whitelist.")
                    continue

            # block_on
            if "all" in matched_block_rule.get("block_on", []) or check_type in matched_block_rule.get("block_on", []):
                is_whitelisted = (
                    any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_for_project) or
                    any(fnmatch.fnmatch(package_name, wl) for wl in whitelist_nugets) or
                    allow_all
                )
                if not is_whitelisted:
                    log_summary(f"ERROR: Found blocked package '{package_name}' in {csproj_path}.")
                    blocked_found = True
                else:
                    log_summary(f"WARNING: Package '{package_name}' would be blocked but is allowed by whitelist.")

    return not blocked_found


def check_all_projects(blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
    csprojs = find_csproj_files()
    if not csprojs:
        log_summary("No .csproj files found")
        return True

    ok = True
    for csproj in csprojs:
        if uses_packages_config(csproj):
            if not check_packages_config(csproj, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
                ok = False
            continue

        if is_classic_web_app(csproj):
            if os.name != "nt" or not web_targets_present():
                log_summary(f"WARNING: Skipping classic ASP.NET project {csproj}")
                continue

        # Ejecutar los 3 tipos de chequeo
        for check_type in ("outdated", "vulnerable", "deprecated"):
            if not run_dotnet_package_check(csproj, check_type, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
                ok = False

    return ok
