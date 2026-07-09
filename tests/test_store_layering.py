"""store 層の逆向き依存回帰テスト (Ticket T45).

DESIGN.md §5「逆向き依存禁止: collect → store ← deliver」より、store は最下層の
ハブであり edit/ や script/ の上位ドメイン型を import してはならない。
"""
from __future__ import annotations

import ast
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent.parent / "src" / "karyu_tech_news" / "store"
FORBIDDEN_PREFIXES = ("karyu_tech_news.edit", "karyu_tech_news.script")


def _imported_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_store_does_not_import_edit_or_script() -> None:
    """store/ 配下の各モジュールが edit/ や script/ を import していないこと."""
    offenders: dict[str, set[str]] = {}
    for py_file in sorted(STORE_DIR.glob("*.py")):
        modules = _imported_modules(py_file)
        forbidden = {
            m for m in modules if any(m.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
        }
        if forbidden:
            offenders[py_file.name] = forbidden

    assert not offenders, (
        "store/ は edit/ や script/ の上位ドメイン型を import してはならない "
        f"(DESIGN.md §5): {offenders}"
    )
