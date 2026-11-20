from ixh26 import cli


def test_smoke_runs_offline() -> None:
    assert cli.main(["smoke"]) == 0


def test_config_never_prints_secret(capsys, monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "s3cr3t-value-" * 4)
    assert cli.main(["config"]) == 0
    out = capsys.readouterr().out
    assert "s3cr3t-value" not in out
    assert "JWT_SECRET       set" in out
