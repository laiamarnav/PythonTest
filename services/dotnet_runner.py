import os
import subprocess
from typing import List

from core.logger import Logger

NUGET_SOURCES = [
    "https://vueling.pkgs.visualstudio.com/_packaging/vy-nuget/nuget/v3/index.json",
    "https://api.nuget.org/v3/index.json",
]


class DotnetRunner:
    def __init__(self, sources: List[str] | None = None, logger: Logger | None = None):
        self.sources = sources or NUGET_SOURCES
        self.logger = logger or Logger()

    def restore(self, target_path: str) -> bool:
        cmd = ["dotnet", "restore", target_path]
        for source in self.sources:
            cmd.extend(["--source", source])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        self.logger.info(f"\n[RESTORE] {os.path.abspath(target_path)}")
        if r.stdout:
            self.logger.info(r.stdout)
        if r.returncode != 0:
            self.logger.error(f"ERROR: dotnet restore failed for {target_path} (code {r.returncode}).")
            if r.stderr:
                self.logger.error(f"[dotnet stderr]\n{r.stderr}")
            return False
        return True

    def list_packages(self, csproj_path: str, check_type: str):
        cmd = ["dotnet", "list", csproj_path, "package", f"--{check_type}", "--include-transitive"]
        for source in self.sources:
            cmd.extend(["--source", source])
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        self.logger.info(f"\n [{check_type.upper()} PACKAGES] ")
        self.logger.info("-" * 60)
        self.logger.info(f"\nChecking packages for {os.path.abspath(csproj_path)}")
        if result.stdout:
            self.logger.info(result.stdout)
        return result
