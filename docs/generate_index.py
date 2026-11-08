#!/usr/bin/env python3
"""Automated HTML Document Indexer for SRE Captura Física e Digital — Docs Hub.

Scans subdirectories of docs/ (runbooks, arquiteturas, procedimentos, apresentacoes),
extracts title, description, headings, and searchable full-text content using Python's
native html.parser, queries git history for last modification date (with filesystem
mtime fallback), and writes docs/docs.json.
"""

import json
import re
import subprocess
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

ALLOWED_CATEGORIES = (
    "arquiteturas",
    "runbooks",
    "procedimentos",
    "apresentacoes",
)


class DocumentMetadataParser(HTMLParser):
    """Extracts <title>, headings, <meta name="description">, and full visible text for search."""

    IGNORED_TAGS = frozenset({"script", "style", "noscript", "svg"})
    HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_text: list[str] = []
        self.h1_text: list[str] = []
        self.first_p_text: list[str] = []
        self.headings: list[str] = []
        self.body_words: list[str] = []

        self._in_title = False
        self._in_first_h1 = False
        self._found_h1 = False
        self._in_first_p = False
        self._found_p = False
        self._in_heading = False
        self._current_heading_parts: list[str] = []
        self._ignored_depth = 0

        self.meta_description: str | None = None
        self.meta_keywords: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth > 0:
            return

        attr_dict = {k.lower(): (v or "") for k, v in attrs if k}

        if tag_lower == "title" and not self.title_text:
            self._in_title = True
        elif tag_lower == "h1" and not self._found_h1:
            self._in_first_h1 = True
        elif tag_lower == "p" and not self._found_p:
            self._in_first_p = True
        elif tag_lower == "meta":
            meta_name = attr_dict.get("name", "").strip().lower()
            content = attr_dict.get("content", "").strip()
            if meta_name == "description" and content and not self.meta_description:
                self.meta_description = self._clean_whitespace(content)
            elif meta_name in ("tags", "keywords") and content and not self.meta_keywords:
                self.meta_keywords = [t.strip() for t in content.split(",") if t.strip()]

        if tag_lower in ("body", "header", "h1", "h2", "h3", "p", "div", "section"):
            self._in_title = False

        if tag_lower in self.HEADING_TAGS:
            if self._in_heading:
                prev = self._clean_whitespace("".join(self._current_heading_parts))
                if prev:
                    self.headings.append(prev)
                self._current_heading_parts.clear()
            self._in_heading = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.IGNORED_TAGS:
            if self._ignored_depth > 0:
                self._ignored_depth -= 1
            return
        if self._ignored_depth > 0:
            return

        if tag_lower == "title" and self._in_title:
            self._in_title = False
        elif tag_lower == "h1" and self._in_first_h1:
            self._in_first_h1 = False
            self._found_h1 = True
        elif tag_lower == "p" and self._in_first_p:
            self._in_first_p = False
            if self._clean_whitespace("".join(self.first_p_text)):
                self._found_p = True
            else:
                self.first_p_text.clear()

        if tag_lower in self.HEADING_TAGS and self._in_heading:
            self._in_heading = False
            heading_str = self._clean_whitespace("".join(self._current_heading_parts))
            if heading_str:
                self.headings.append(heading_str)
            self._current_heading_parts.clear()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        if self._in_title:
            self.title_text.append(data)
        if self._in_first_h1:
            self.h1_text.append(data)
        if self._in_first_p:
            self.first_p_text.append(data)
        if self._in_heading:
            self._current_heading_parts.append(data)
        self.body_words.append(data)

    @staticmethod
    def _clean_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def get_title(self, fallback_filename: str) -> str:
        raw_title = self._clean_whitespace("".join(self.title_text))
        raw_h1 = self._clean_whitespace("".join(self.h1_text))

        if raw_title:
            cleaned = re.split(r"\s+[\|—–-]\s+SRE\b", raw_title, maxsplit=1)[0].strip()
            return cleaned or raw_title
        if raw_h1:
            return raw_h1

        stem = Path(fallback_filename).stem
        return stem.replace("-", " ").replace("_", " ").title()

    def get_description(self) -> str:
        if self.meta_description:
            return self.meta_description
        raw_p = self._clean_whitespace("".join(self.first_p_text))
        if raw_p:
            return raw_p
        return "Documentação técnica oficial mantida pela equipe de SRE Captura Física e Digital."

    def get_search_text(self) -> str:
        """Builds a deduplicated, compact full-text search string from headings, keywords, and body."""
        raw_parts = [
            " ".join(self.meta_keywords),
            " ".join(self.headings),
            " ".join(self.body_words),
        ]
        combined = self._clean_whitespace(" ".join(p for p in raw_parts if p))
        seen: set[str] = set()
        unique_tokens: list[str] = []
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9_./:-]{2,}", combined):
            low = token.lower()
            if low not in seen:
                seen.add(low)
                unique_tokens.append(token)
        return " ".join(unique_tokens)


def get_last_updated_date(file_path: Path, repo_root: Path) -> str:
    """Returns YYYY-MM-DD from `git log -1 --format=%cs`, or falls back to filesystem mtime."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(file_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        git_date = result.stdout.strip()
        if result.returncode == 0 and re.match(r"^\d{4}-\d{2}-\d{2}$", git_date):
            return git_date
    except (subprocess.SubprocessError, OSError):
        pass

    mtime = file_path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=UTC).astimezone().strftime("%Y-%m-%d")


def parse_html_file(file_path: Path, docs_dir: Path, repo_root: Path) -> dict[str, object]:
    """Parses a single HTML file inside docs/ and returns its catalog dictionary."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    parser = DocumentMetadataParser()
    parser.feed(content)

    rel_path = file_path.relative_to(docs_dir)
    category = rel_path.parts[0] if len(rel_path.parts) > 1 else "geral"

    return {
        "title": parser.get_title(file_path.name),
        "description": parser.get_description(),
        "category": category,
        "path": rel_path.as_posix(),
        "updated_at": get_last_updated_date(file_path, repo_root),
        "search_text": parser.get_search_text(),
    }


def build_index() -> list[dict[str, object]]:
    """Scans docs/ subdirectories and writes docs/docs.json."""
    docs_dir = Path(__file__).resolve().parent
    repo_root = docs_dir.parent

    documents: list[dict[str, object]] = []

    for category in ALLOWED_CATEGORIES:
        category_dir = docs_dir / category
        if not category_dir.exists() or not category_dir.is_dir():
            continue

        for html_file in sorted(category_dir.rglob("*.html")):
            if html_file.resolve() == (docs_dir / "index.html").resolve():
                continue
            doc_entry = parse_html_file(html_file, docs_dir, repo_root)
            documents.append(doc_entry)

    # Default sort: updated_at descending, then title ascending
    documents.sort(key=lambda d: str(d.get("title", "")).lower())
    documents.sort(key=lambda d: str(d.get("updated_at", "")), reverse=True)

    output_path = docs_dir / "docs.json"
    output_path.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[generate_index] Indexed {len(documents)} HTML document(s) -> {output_path}")
    return documents


if __name__ == "__main__":
    build_index()
