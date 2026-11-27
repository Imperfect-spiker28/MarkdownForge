"""Core Markdown TOC generation, link linting, and HTML export."""

from dataclasses import dataclass
import html
from pathlib import Path
import re
from typing import Any

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class LintIssue:
    file: str
    line: int
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "message": self.message,
        }


def slugify_heading(text: str) -> str:
    """Create a GitHub-style anchor slug from heading text."""
    cleaned = re.sub(r"[`*_~]", "", text).strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned


def extract_headings(markdown: str) -> list[tuple[int, str, str]]:
    """Return list of (level, text, slug) outside fenced code blocks."""
    headings: list[tuple[int, str, str]] = []
    in_fence = False
    slug_counts: dict[str, int] = {}

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            base_slug = slugify_heading(title)
            count = slug_counts.get(base_slug, 0)
            slug_counts[base_slug] = count + 1
            slug = base_slug if count == 0 else f"{base_slug}-{count}"
            headings.append((level, title, slug))

    return headings


def build_toc(markdown: str, max_depth: int = 3) -> str:
    """Generate a Markdown bullet-list Table of Contents."""
    headings = [h for h in extract_headings(markdown) if h[0] <= max_depth]
    if not headings:
        return ""
    min_level = min(h[0] for h in headings)
    lines = [
        f"{'  ' * (lvl - min_level)}- [{title}](#{slug})"
        for lvl, title, slug in headings
    ]
    return "\n".join(lines)


def inject_toc(markdown: str, max_depth: int = 3) -> str:
    """Replace content between <!-- TOC --> and <!-- /TOC --> markers."""
    toc_block = build_toc(markdown, max_depth=max_depth)
    pattern = re.compile(r"(<!--\s*TOC\s*-->)(.*?)(<!--\s*/TOC\s*-->)", re.DOTALL)
    if not pattern.search(markdown):
        return toc_block
    return pattern.sub(rf"\1\n{toc_block}\n\3", markdown, count=1)


def lint_markdown_file(md_path: Path) -> list[LintIssue]:
    """Check a Markdown file for unclosed fences and broken local relative links."""
    issues: list[LintIssue] = []
    content = md_path.read_text(encoding="utf-8")
    in_fence = False
    fence_start_line = 0

    for line_no, line in enumerate(content.splitlines(), start=1):
        if line.strip().startswith("```"):
            if not in_fence:
                fence_start_line = line_no
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for _, target in _LINK_RE.findall(line):
            target = target.strip().split(" ", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            rel_path = target.split("#", 1)[0]
            if rel_path and not (md_path.parent / rel_path).exists():
                issues.append(
                    LintIssue(
                        file=str(md_path),
                        line=line_no,
                        severity="ERROR",
                        message=f"Broken relative link: {target}",
                    )
                )

    if in_fence:
        issues.append(
            LintIssue(
                file=str(md_path),
                line=fence_start_line,
                severity="ERROR",
                message="Unclosed fenced code block (```)",
            )
        )

    return issues


def _render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def export_html(markdown: str, title: str = "Document") -> str:
    """Convert Markdown text into a standalone HTML5 document."""
    body: list[str] = []
    in_fence = False
    in_list = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            body.append("</ul>")
            in_list = False

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            close_list()
            if not in_fence:
                in_fence = True
                code_lines = []
            else:
                in_fence = False
                code_html = html.escape("\n".join(code_lines))
                body.append(f"<pre><code>{code_html}</code></pre>")
            continue

        if in_fence:
            code_lines.append(line)
            continue

        if not stripped:
            close_list()
            continue

        m = _HEADING_RE.match(line)
        if m:
            close_list()
            lvl = len(m.group(1))
            heading_text = m.group(2).strip()
            slug = slugify_heading(heading_text)
            body.append(f'<h{lvl} id="{slug}">{_render_inline(heading_text)}</h{lvl}>')
            continue

        if stripped.startswith(("- ", "* ")):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_render_inline(stripped[2:].strip())}</li>")
            continue

        if stripped.startswith("> "):
            close_list()
            body.append(f"<blockquote>{_render_inline(stripped[2:].strip())}</blockquote>")
            continue

        close_list()
        body.append(f"<p>{_render_inline(stripped)}</p>")

    close_list()
    inner = "\n  ".join(body)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="utf-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f"  <title>{html.escape(title)}</title>\n"
        "  <style>body{font-family:system-ui,sans-serif;max-width:820px;margin:2.5rem auto;padding:0 1.25rem;line-height:1.65;color:#111}pre{background:#f5f5f5;padding:1rem;overflow:auto;border-radius:6px}code{font-family:ui-monospace,monospace;font-size:.9em}blockquote{border-left:3px solid #ddd;margin:1rem 0;padding-left:1rem;color:#555}</style>\n"
        "</head>\n<body>\n"
        f"  {inner}\n"
        "</body>\n</html>\n"
    )
