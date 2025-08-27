import tempfile, os
from checks.legacy_config_check import check_packages_config

def test_blocked_package_detected():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="log4net" version="1.2.10" targetFramework="net472" />
</packages>"""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = os.path.join(tmpdir, "packages.config")
        csproj = os.path.join(tmpdir, "fake.csproj")
        open(csproj, "w").write("<Project/>")
        open(pkg_path, "w").write(xml)

        blocked = [{"name": "log4net", "block_on": ["all"], "min_version": "2.0.0"}]
        ok = check_packages_config(csproj, blocked, {}, [], "")
        assert not ok  
