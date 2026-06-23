"""Import conventions: business code must use utils.net as the URL/domain facade."""

from __future__ import annotations

import ast
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1] / "src" / "aperix_geo"
_FORBIDDEN_MODULES = frozenset({"aperix_geo.utils.domains", "aperix_geo.utils.url"})
_ALLOWED_REL_PATHS = frozenset(
    {
        "utils/net.py",
        "utils/domains.py",
        "utils/url.py",
    }
)


def _iter_python_files() -> list[Path]:
    return sorted(_PKG_ROOT.rglob("*.py"))


def _rel_path(path: Path) -> str:
    return path.relative_to(_PKG_ROOT).as_posix()


def _find_forbidden_imports(path: Path) -> list[str]:
    rel = _rel_path(path)
    if rel in _ALLOWED_REL_PATHS:
        return []

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _FORBIDDEN_MODULES:
            hits.append(f"{rel}:{node.lineno} imports {node.module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _FORBIDDEN_MODULES:
                    hits.append(f"{rel}:{node.lineno} imports {alias.name}")
    return hits


def test_business_modules_import_net_facade_only() -> None:
    violations: list[str] = []
    for path in _iter_python_files():
        violations.extend(_find_forbidden_imports(path))
    assert not violations, "Use aperix_geo.utils.net instead:\n" + "\n".join(violations)
