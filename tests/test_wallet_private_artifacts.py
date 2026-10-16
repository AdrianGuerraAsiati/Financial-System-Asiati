"""Guardarraíl: nunca incorporar fixtures, baselines o Excel reales a Git."""
import subprocess
from pathlib import Path


def test_private_wallet_files_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert "fixtures/" in gitignore
    assert "secrets/" in gitignore


def test_no_operational_fixture_is_committed():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        check=True, capture_output=True,
    )
    archivos = [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    assert not any(p.startswith(("fixtures/", "secrets/")) for p in archivos)
    assert not any(
        p.endswith((".xlsx", ".xls", ".xlsm", ".csv", ".zip"))
        for p in archivos
    )
    assert not any(
        p.endswith(("expected_baseline.json", "expected_recompra_menpros.json"))
        for p in archivos
    )
