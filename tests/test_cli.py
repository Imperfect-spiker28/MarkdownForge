import json
from pathlib import Path

from markdownforge.cli import main


def test_cli_lint_and_export_roundtrip(tmp_path: Path, capsys) -> None:
    md = tmp_path / "guide.md"
    out_html = tmp_path / "guide.html"
    md.write_text("# Guide\n\nClean text.\n", encoding="utf-8")

    assert main(["lint", str(md), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True

    assert main(["export", str(md), "-o", str(out_html)]) == 0
    assert out_html.exists()
    assert '<h1 id="guide">Guide</h1>' in out_html.read_text(encoding="utf-8")
