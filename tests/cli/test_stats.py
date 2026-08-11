from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def test_stats_basic():
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "No snippets in your collection yet" in result.output or "SnipContext Stats" in result.output


def test_stats_json():
    result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "total_snippets" in result.output or "data_dir" in result.output
