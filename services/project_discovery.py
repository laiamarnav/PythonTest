import glob
from typing import List


def find_csproj_files() -> List[str]:
    return glob.glob("**/*.csproj", recursive=True)


def find_sln_files() -> List[str]:
    return glob.glob("*.sln")
