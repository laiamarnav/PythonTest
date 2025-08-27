import argparse
import sys
from services.scanner_service import run_nuget_validation

def main():
    parser = argparse.ArgumentParser(description="NuGet packages validator")
    parser.add_argument("--working-dir", required=True, help="Directorio del proyecto a validar")
    parser.add_argument("--blocked", default="settings/blocked_packages.json", help="Ruta al JSON de paquetes bloqueados")
    parser.add_argument("--whitelist", required=True, help="Ruta al JSON de whitelist")
    parser.add_argument("--tag-pr", default="", help="Tag del pull request (para excepciones de beta packages)")
    args = parser.parse_args()

    success, reporter = run_nuget_validation(
        working_dir=args.working_dir,
        blocked_path=args.blocked,
        whitelist_path=args.whitelist,
        tag_pull_request=args.tag_pr
    )

    reporter.write_to_file()

    print("\nSUMMARY REPORT")
    print("-" * 60)
    if reporter.lines:
        for line in reporter.lines:
            print(line)
    else:
        print("No blocked packages or issues found.")

    if hasattr(reporter, "has_errors") and reporter.has_errors():
        sys.exit(1)
    elif hasattr(reporter, "has_warnings") and reporter.has_warnings():
        print("##vso[task.complete result=SucceededWithIssues;]Warnings found in package checks.")
        sys.exit(0)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()