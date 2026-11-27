"""Command-line interface for MarkdownForge."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .engine import build_toc, export_html, inject_toc, lint_markdown_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdownforge",
        description="Generate Markdown TOCs, lint local links, and export standalone HTML.",
    )
    parser.add_argument("--version", action="version", version=f"markdownforge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    toc_cmd = sub.add_parser("toc", help="Generate or update Table of Contents")
    toc_cmd.add_argument("file", type=Path, help="Markdown file")
    toc_cmd.add_argument("--max-depth", type=int, default=3, help="Max heading depth (1-6)")
    toc_cmd.add_argument("--in-place", action="store_true", help="Update <!-- TOC --> markers in place")

    lint_cmd = sub.add_parser("lint", help="Lint Markdown files for broken links & unclosed code fences")
    lint_cmd.add_argument("target", type=Path, help="Markdown file or directory")
    lint_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    exp_cmd = sub.add_parser("export", help="Export Markdown to standalone HTML")
    exp_cmd.add_argument("file", type=Path, help="Input Markdown file")
    exp_cmd.add_argument("-o", "--output", type=Path, default=None, help="Output HTML file")
    exp_cmd.add_argument("--title", default=None, help="HTML page title")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "toc":
        text = args.file.read_text(encoding="utf-8")
        if args.in_place:
            updated = inject_toc(text, max_depth=args.max_depth)
            args.file.write_text(updated, encoding="utf-8")
            print(f"Updated TOC in {args.file}")
        else:
            print(build_toc(text, max_depth=args.max_depth))
        return 0

    if args.command == "lint":
        files = [args.target] if args.target.is_file() else sorted(args.target.rglob("*.md"))
        all_issues = []
        for md_file in files:
            all_issues.extend(lint_markdown_file(md_file))

        if args.json:
            print(json.dumps({"ok": not all_issues, "issue_count": len(all_issues), "issues": [i.to_dict() for i in all_issues]}, indent=2))
        else:
            if not all_issues:
                print(f"[OK] Checked {len(files)} Markdown file(s) — 0 issues")
            else:
                print(f"[FAIL] {len(all_issues)} issue(s) found:")
                for issue in all_issues:
                    print(f"  {issue.file}:{issue.line} [{issue.severity}] {issue.message}")
        return 1 if all_issues else 0

    if args.command == "export":
        text = args.file.read_text(encoding="utf-8")
        title = args.title or args.file.stem
        rendered = export_html(text, title=title)
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Exported HTML to {args.output}")
        else:
            print(rendered)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
