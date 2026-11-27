# MarkdownForge

Zero-dependency Markdown TOC generator, local link linter, and standalone HTML exporter CLI.

## Features
- **TOC Generator (`toc`):** Extracts headings outside fenced code blocks, generates GitHub-compatible anchor slugs, and updates `<!-- TOC -->` blocks in place.
- **Link & Fence Linter (`lint`):** Catches broken relative links and unclosed ```` ``` ```` code blocks across documentation trees, with `--json` CI reporting.
- **HTML Export (`export`):** Converts Markdown into a clean, self-contained HTML5 page with inline typography styling.

## Installation

```bash
pip install -e .
```

## Usage

```bash
markdownforge toc README.md
markdownforge lint examples/sample.md --json
markdownforge export examples/sample.md -o dist/sample.html
```

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```
