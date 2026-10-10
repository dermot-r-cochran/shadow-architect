"""Source check for the repository's Markdown (stdlib only).

Three checks, run by CI on every pull request and push to main:

1. Every relative link in README.md, CLAUDE.md, TestingStrategy.md and the
   pages under docs/ resolves to a file or directory in the repository.
   External links (a scheme such as https:) and in-page anchors are skipped.
2. No Markdown file carries more than one front-matter block (a `---` line
   followed by `key: value` lines and a closing `---`), which is what a stray
   fragment left by a merge or a stacked paste looks like.
3. What the README states matches what is on disk:
   - every test it names as proof (`tests/test_x.py::Class::test_name`, or
     `tests/test_x.py::test_name`) exists, so a README row cannot cite a
     test that is not there;
   - every module tree it draws (a fenced block whose first line is
     `shadow_architect/`) names every module under src/shadow_architect/
     and nothing that is not there, so the count of modules per package in
     the README is the count on disk.

Run from anywhere: python .github/scripts/check_docs.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "shadow_architect"
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
FRONT_KEY = re.compile(r"^[A-Za-z_][\w-]*\s*:")
TEST_REF = re.compile(r"`(tests/test_\w+\.py)::([\w:]+)`")
TREE_LINE = re.compile(r"(?:├──|└──)\s*([^\s#]+)")


def markdown_files() -> list[Path]:
    found = [ROOT / name for name in ("README.md", "CLAUDE.md", "TestingStrategy.md")]
    found += sorted((ROOT / "docs").rglob("*.md"))
    return [path for path in found if path.is_file()]


def fenced_blocks(lines: list[str]) -> tuple[list[tuple[int, str]], list[list[str]]]:
    """Split body lines into prose (with line numbers) and fenced code blocks."""
    prose: list[tuple[int, str]] = []
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
            continue
        if current is None:
            prose.append((number, line))
        else:
            current.append(line)
    return prose, blocks


def front_matter_blocks(lines: list[str]) -> int:
    """Count `---` blocks whose first inner line is a `key:` line."""
    count, i = 0, 0
    while i < len(lines):
        if lines[i].strip() == "---" and i + 1 < len(lines) and FRONT_KEY.match(lines[i + 1]):
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "---":
                    count += 1
                    i = j
                    break
        i += 1
    return count


def tests_on_disk() -> dict[str, set[str]]:
    """Map each tests/test_*.py to the `Class::test` and `test` names it defines."""
    found: dict[str, set[str]] = {}
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        names: set[str] = set()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        names.add(f"{node.name}::{item.name}")
        found[path.relative_to(ROOT).as_posix()] = names
    return found


def modules_on_disk() -> dict[str, set[str]]:
    """Map each package directory (relative to the package root) to its modules."""
    found: dict[str, set[str]] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(PACKAGE)
        found.setdefault(rel.parent.as_posix(), set()).add(path.name)
    return found


def modules_in_tree(block: list[str]) -> dict[str, set[str]]:
    """Read a README module tree into the same shape as modules_on_disk()."""
    found: dict[str, set[str]] = {}
    directory = "."
    for line in block[1:]:
        match = TREE_LINE.search(line)
        if not match:
            continue
        name = match.group(1)
        depth = match.start() // 4
        if name.endswith("/"):
            directory = name.rstrip("/")
        elif name.endswith(".py"):
            found.setdefault(directory if depth else ".", set()).add(name)
    return found


def main() -> int:
    errors: list[str] = []
    disk_tests = tests_on_disk()
    disk_modules = modules_on_disk()

    for path in markdown_files():
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        prose, blocks = fenced_blocks(lines)

        blocks_found = front_matter_blocks(lines)
        if blocks_found > 1:
            errors.append(f"{rel}: {blocks_found} front-matter blocks (at most one allowed)")

        for number, line in prose:
            for match in LINK.finditer(line):
                target = match.group(1)
                if SCHEME.match(target) or target.startswith("#"):
                    continue
                target_path = target.split("#", 1)[0].split("?", 1)[0]
                if not (path.parent / target_path).exists():
                    errors.append(f"{rel}:{number}: link {target!r} resolves to no file")

        if rel != "README.md":
            continue

        for number, line in prose:
            for match in TEST_REF.finditer(line):
                file, name = match.group(1), match.group(2)
                if name not in disk_tests.get(file, set()):
                    errors.append(f"{rel}:{number}: cites {file}::{name}, which does not exist")

        for block in blocks:
            if not block or block[0].strip() != "shadow_architect/":
                continue
            stated = modules_in_tree(block)
            for directory in sorted(set(stated) | set(disk_modules)):
                missing = sorted(disk_modules.get(directory, set()) - stated.get(directory, set()))
                extra = sorted(stated.get(directory, set()) - disk_modules.get(directory, set()))
                if missing:
                    errors.append(f"{rel}: module tree omits {directory}/{{{', '.join(missing)}}}")
                if extra:
                    names = ", ".join(extra)
                    errors.append(f"{rel}: module tree names {directory}/{{{names}}}, not on disk")

    for error in errors:
        print(error)
    print(f"{len(markdown_files())} files, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
