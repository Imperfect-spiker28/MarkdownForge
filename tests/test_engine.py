from pathlib import Path

from markdownforge.engine import build_toc, export_html, inject_toc, lint_markdown_file


def test_build_and_inject_toc_skips_code_fences() -> None:
    md = """# Title
<!-- TOC -->
old
<!-- /TOC -->

```bash
# Not a heading
```

## Setup
### Install
"""
    toc = build_toc(md)
    assert "Not a heading" not in toc
    assert "- [Setup](#setup)" in toc
    assert "  - [Install](#install)" in toc

    updated = inject_toc(md)
    assert "old" not in updated
    assert "- [Setup](#setup)" in updated


def test_lint_detects_broken_link_and_unclosed_fence(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("# Doc\n[Missing](./nope.md)\n```python\nx = 1\n", encoding="utf-8")
    issues = lint_markdown_file(md_file)
    assert len(issues) == 2
    assert any("Broken relative link" in i.message for i in issues)
    assert any("Unclosed fenced code block" in i.message for i in issues)


def test_export_html_renders_headings_lists_and_code() -> None:
    html_out = export_html("# Hello\n\n- **Bold** item\n\n```\ncode()\n```\n", title="Test")
    assert "<title>Test</title>" in html_out
    assert '<h1 id="hello">Hello</h1>' in html_out
    assert "<li><strong>Bold</strong> item</li>" in html_out
    assert "<pre><code>code()</code></pre>" in html_out
