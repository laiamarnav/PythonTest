import tempfile, os
from services.scanner_service import check_all_projects

def test_integration_with_blocked_package():
    with tempfile.TemporaryDirectory() as tmpdir:
        projdir = os.path.join(tmpdir, "MyApp")
        os.makedirs(projdir)
        csproj = os.path.join(projdir, "MyApp.csproj")
        open(csproj, "w").write("<Project/>")

        pkg = os.path.join(projdir, "packages.config")
        with open(pkg, "w") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
            <packages>
            <package id="log4net" version="1.2.10" targetFramework="net472" />
            </packages>""")
        blocked = [{"name": "log4net", "block_on": ["all"], "min_version": "2.0.0"}]


        wl_projects, wl_nugets = {}, []

        cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            ok = check_all_projects(blocked, wl_projects, wl_nugets, "")
            assert not ok
        finally:
            os.chdir(cwd)
