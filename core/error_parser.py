import os
from typing import Tuple


def parse_dotnet_error(stderr: str, csproj_path: str) -> Tuple[str, str, bool]:
    """Interpret common dotnet CLI errors.

    Returns a tuple (severity, message, skip_ok) where ``skip_ok`` indicates
    whether the project can be skipped without failing the scan.
    """
    s = (stderr or "").lower()

    if "no assets file was found" in s:
        return (
            "WARNING",
            f"{csproj_path}: No assets file. Run 'dotnet restore' (o verifica feeds/credenciales).",
            True,
        )

    if "package.config" in s:
        return (
            "WARNING",
            f"{csproj_path}: Proyecto con packages.config (no soportado por 'dotnet list'). Se omite.",
            True,
        )

    if "microsoft.webapplication.targets" in s:
        hint = (
            "Instala Visual Studio Build Tools 2022 (Web Build Tools) en un agente Windows."
            if os.name == "nt"
            else "Ejecuta en agente Windows con VS Build Tools (Web)."
        )
        return (
            "WARNING",
            f"{csproj_path}: Proyecto ASP.NET clásico sin Web targets. {hint} Se omite.",
            True,
        )

    if (
        "unrecognized option '--vulnerable'" in s
        or "unrecognized option '--deprecated'" in s
        or "unrecognized option '--outdated'" in s
    ):
        return (
            "ERROR",
            f"{csproj_path}: El SDK de .NET es antiguo. Necesitas .NET SDK 5+ para '--vulnerable/--deprecated/--outdated'.",
            False,
        )

    if (
        "unable to load the service index for source" in s
        or "nu1301" in s
        or "nu1100" in s
    ):
        return (
            "ERROR",
            f"{csproj_path}: Problema con las fuentes de NuGet (feed/credenciales/red). Revisa autenticación y accesibilidad de los feeds.",
            False,
        )

    return ("ERROR", f"{csproj_path}: dotnet list package falló. Revisa stderr arriba.", False)
