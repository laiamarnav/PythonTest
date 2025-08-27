from core.utils import version_lt

def test_version_lt_basic():
    assert version_lt("1.0.0", "2.0.0")
    assert not version_lt("2.0.0", "1.0.0")
    assert not version_lt("1.0.0", "1.0.0")

def test_version_lt_handles_missing():
    assert version_lt("1.0", "1.0.1")
    assert not version_lt("1.0.1", "1.0")
