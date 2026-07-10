"""store 層の逆向き依存回帰テスト (Ticket T45).

DESIGN.md §5「逆向き依存禁止: collect → store ← deliver」より、store は最下層の
ハブであり edit/ や script/ の上位ドメイン型を import してはならない。
"""
from __future__ import annotations

import ast
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent.parent / "src" / "karyu_tech_news" / "store"
# 絶対 import (karyu_tech_news.edit...) と相対 import (..edit...) の両方を捕捉するため、
# 末端パッケージ名 edit / script も禁止語に含める。
FORBIDDEN_SEGMENTS = ("karyu_tech_news.edit", "karyu_tech_news.script", "edit", "script")


def _is_forbidden(module: str) -> bool:
    """module がドット区切りセグメント境界で禁止パッケージに一致するか.

    ``editor_utils`` や ``scripting`` のような別語を誤検出しないよう、完全一致か
    ``<forbidden>.`` で始まる場合のみ真とする (startswith の部分一致は使わない)。
    """
    return any(
        module == seg or module.startswith(f"{seg}.") for seg in FORBIDDEN_SEGMENTS
    )


def _imported_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # 絶対 import は module をそのまま。相対 import (level>0、例 `from ..edit.judge`)
            # は module 文字列 ("edit.judge") をそのまま見ることで edit/script リークを検出する。
            if node.module:
                modules.add(node.module)
            # `from karyu_tech_news import edit` / `from .. import script` のように、
            # 禁止パッケージ名が imported name 側 (node.names) に出る形式も捕捉する。
            # module + name を結合したフルパスと、name 単体の両方を候補に加える。
            for alias in node.names:
                if node.module:
                    modules.add(f"{node.module}.{alias.name}")
                modules.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_store_does_not_import_edit_or_script() -> None:
    """store/ 配下の各モジュール (サブパッケージ含む) が edit/ や script/ を import しないこと."""
    offenders: dict[str, set[str]] = {}
    for py_file in sorted(STORE_DIR.rglob("*.py")):
        modules = _imported_modules(py_file)
        forbidden = {m for m in modules if _is_forbidden(m)}
        if forbidden:
            offenders[py_file.name] = forbidden

    assert not offenders, (
        "store/ は edit/ や script/ の上位ドメイン型を import してはならない "
        f"(DESIGN.md §5): {offenders}"
    )
