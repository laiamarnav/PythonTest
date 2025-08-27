import tempfile, os
from checks.legacy_config_check import check_packages_config
from core.utils import uses_packages_config

def make_fake_packages_config(tmpdir, packages):
    pkg_path = os.path.join(tmpdir, "packages.config")
    csproj = os.path.join(tmpdir, "fake.csproj")
    open(csproj, "w").write("<Project/>")

    with open(pkg_path, "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<packages>\n')
        for name, version in packages:
            f.write(f'  <package id="{name}" version="{version}" targetFramework="net472" />\n')
        f.write('</packages>')
    return csproj

def test_detects_packages_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        csproj = make_fake_packages_config(tmpdir, [("Newtonsoft.Json","9.0.1")])
        assert uses_packages_config(csproj)

def test_blocked_package_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        csproj = make_fake_packages_config(tmpdir, [("log4net","1.2.10")])
        blocked = [{"name": "log4net", "block_on": ["all"], "min_version": "2.0.0"}]
        ok = check_packages_config(csproj, blocked, {}, [], "")
        assert not ok

def test_allowed_package_passes():
    with tempfile.TemporaryDirectory() as tmpdir:
        csproj = make_fake_packages_config(tmpdir, [("xunit","2.4.1")])
        blocked = [{"name": "log4net", "block_on": ["all"], "min_version": None}]
        ok = check_packages_config(csproj, blocked, {}, [], "")
        assert ok
