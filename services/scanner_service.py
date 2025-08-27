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
from checks.checks import Check 


def _is_web_targets_error(stderr: str) -> bool:
    s = (stderr or "").lower()
    return "microsoft.webapplication.targets" in s


def _is_packages_config_error(stderr: str) -> bool:
    s = (stderr or "").lower()
    return ("uses package.config" in s) or ("package.config" in s)


def _run_modern_checks_by_solution(slns, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner, reporter) -> (bool, bool):
    ok = True
    need_fallback = False

    checks = [
        Check("outdated",   runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("vulnerable", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("deprecated", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
    ]

    for sln in slns:
        for check in checks:
            res = runner.list_packages(sln, check.check_type)

            if res.returncode != 0:
                if _is_web_targets_error(res.stderr) or _is_packages_config_error(res.stderr):
                    need_fallback = True
                reporter.add(f"ERROR: {os.path.basename(sln)}: dotnet list package falló. Revisa stderr arriba.")
                if res.stderr:
                    runner.logger.error(res.stderr)
                ok = False
            else:
                if not check.run(sln):
                    ok = False

    return ok, need_fallback


def _run_legacy_for_packages_config(csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, reporter) -> bool:
    legacy_ok = True
    for csproj in csprojs:
        if uses_packages_config(csproj):
            if not check_packages_config(csproj, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr):
                legacy_ok = False
    return legacy_ok


def _run_modern_checks_by_project_parallel(csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner, reporter) -> bool:
    checks = [
        Check("outdated",   runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("vulnerable", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
        Check("deprecated", runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr),
    ]

    def run_all_checks_for_project(csproj: str) -> bool:
        if uses_packages_config(csproj):
            return True

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


def check_all_projects(blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner=None, reporter=None):
    runner = runner or DotnetRunner()
    reporter = reporter or SummaryReporter()

    slns = find_sln_files()
    csprojs = find_csproj_files()

    if slns:
        ok_sln, need_fallback = _run_modern_checks_by_solution(
            slns, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner, reporter
        )

        legacy_ok = _run_legacy_for_packages_config(csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, reporter)

        if not need_fallback:
            return ok_sln and legacy_ok

        reporter.add("WARNING: Falling back to per-project checks due to classic web/projects with packages.config.")
        modern_ok = _run_modern_checks_by_project_parallel(
            csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner, reporter
        )
        return modern_ok and legacy_ok

    if not csprojs:
        reporter.add("No .csproj files found")
        return True

    modern_ok = _run_modern_checks_by_project_parallel(
        csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, runner, reporter
    )
    legacy_ok = _run_legacy_for_packages_config(
        csprojs, blocked_packages, whitelist_projects, whitelist_nugets, tag_pr, reporter
    )
    return modern_ok and legacy_ok


def run_nuget_validation(working_dir, blocked_path, whitelist_path, tag_pull_request):
    logger = Logger()
    reporter = SummaryReporter(logger)
    runner = DotnetRunner(logger=logger)

    os.chdir(working_dir)

    blocked_packages = load_blocked_packages(blocked_path)
    whitelist_projects, whitelist_nugets = load_whitelist_data(whitelist_path)

    slns = find_sln_files()
    csprojs = find_csproj_files()

    restored_ok = True
    if slns:
        if not runner.restore(slns[0]):
            restored_ok = False
    else:
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
