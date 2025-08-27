import glob
import os
from typing import List

def find_csproj_files() -> List[str]:
    return [os.path.abspath(p) for p in glob.glob("**/*.csproj", recursive=True)]

def find_sln_files() -> List[str]:
    return [os.path.abspath(p) for p in glob.glob("*.sln")]
