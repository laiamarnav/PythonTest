import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.blocked_packages_loader import load_blocked_packages
from config.whitelist_loader import load_whitelist_data
from core.logger import Logger
from core.utils import (
    is_classic_web_app,
    uses_packages_config,
    web_targets_present,
)
from reports.summary_reporter import SummaryReporter
from services.dotnet_runner import DotnetRunner
from services.project_discovery import find_csproj_files, find_sln_files
from checks.legacy_config_check import check_packages_config
from checks.checks import Check  # clase única con check_type


def check_all_projects(blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner=None, reporter=None):
    """
    - Si hay .sln: ejecuta los checks modernos (deprecated/outdated/vulnerable) a nivel solución
      y además hace una pasada LEGACY para proyectos con packages.config.
    - Si no hay .sln: ejecuta por proyecto en paralelo (e incluye el check LEGACY si aplica).
    """
    runner = runner or DotnetRunner()
    reporter = reporter or SummaryReporter()

    slns = find_sln_files()
    if slns:
        ok = True
        # A) Checks modernos a nivel solución (más rápido)
        checks = [
            Check("outdated",   runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
            Check("vulnerable", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
            Check("deprecated", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        ]
        for sln in slns:
            for check in checks:
                if not check.run(sln):
                    ok = False

        # B) Pasada LEGACY para projects con packages.config
        legacy_ok = True
        csprojs = find_csproj_files()
        for csproj in csprojs:
            if uses_packages_config(csproj):
                if not check_packages_config(csproj, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
                    legacy_ok = False

        return ok and legacy_ok

    # --- Sin .sln: camino actual (paralelizado por proyecto) ---
    csprojs = find_csproj_files()
    if not csprojs:
        reporter.add("No .csproj files found")
        return True

    checks = [
        Check("outdated",   runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("vulnerable", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("deprecated", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
    ]

    def run_all_checks_for_project(csproj: str) -> bool:
        # LEGACY: packages.config
        if uses_packages_config(csproj):
            return check_packages_config(csproj, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr)

        # Proyectos ASP.NET clásicos sin Web targets (solo en Windows con VS Build Tools)
        if is_classic_web_app(csproj):
            if os.name != "nt" or not web_targets_present():
                reporter.add(f"WARNING: Skipping classic ASP.NET project {csproj}")
                return True

        proj_ok = True
        for check in checks:
            if not check.run(csproj):
                proj_ok = False
        return proj_ok

    ok = True
    workers = int(os.getenv("NUGET_CHECK_WORKERS", "4"))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(run_all_checks_for_project, p) for p in csprojs]
        for fut in as_completed(futures):
            if not fut.result():
                ok = False

    return ok


def run_nuget_validation(working_dir, blocked_path, whitelist_path, tag_pull_request):
    """
    - Cambia al directorio de trabajo.
    - Carga blocked/whitelist.
    - Restaura una sola vez (sln si existe; si no, primer .csproj).
    - Ejecuta check_all_projects (modo .sln + LEGACY o por proyecto paralelo).
    - Devuelve (success, reporter).
    """
    logger = Logger()
    reporter = SummaryReporter(logger)
    runner = DotnetRunner(logger=logger)

    os.chdir(working_dir)

    blocked_packages = load_blocked_packages(blocked_path)
    whitelist_projects, whitelist_nugets = load_whitelist_data(whitelist_path)

    # Restaurar una sola vez: usa la solución si existe; si no, primer .csproj
    slns = find_sln_files()
    restored_ok = True
    if slns:
        if not runner.restore(slns[0]):
            restored_ok = False
    else:
        csprojs = find_csproj_files()
        if not csprojs:
            reporter.add("No .csproj files found to restore. Exiting...")
            reporter.write_to_file()
            return True, reporter
        if not runner.restore(csprojs[0]):
            restored_ok = False

    if not restored_ok:
        reporter.add("ERROR: Restore failed. Aborting package checks.")
        reporter.write_to_file()
        return False, reporter

    success = check_all_projects(
        blocked_packages, whitelist_projects, whitelist_nugets, tag_pull_request, runner, reporter
    )

    reporter.write_to_file()
    return success and not reporter.has_errors(), reporter
