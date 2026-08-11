from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def test_migrate_dry_run():
    result = runner.invoke(app, ["migrate", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output or "already at the latest" in result.output


def test_migrate_stub_output():
    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 1
    assert "Automatic migration is not yet implemented" in result.output


def test_migrate_check_when_no_meta(tmp_path, monkeypatch):
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNIPCONTEXT_HOME", raising=False)
    home = tmp_path / ".snipcontext"
    home.mkdir()
    monkeypatch.setenv("SNIPCONTEXT_HOME", str(home))

    result = runner.invoke(app, ["migrate", "check"])
    assert result.exit_code == 0
    assert "0.0.0" in result.output or "behind" in result.output
