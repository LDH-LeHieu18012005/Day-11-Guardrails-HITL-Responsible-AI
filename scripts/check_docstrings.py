"""Check public functions/classes for docstrings."""
import ast
from pathlib import Path


missing = []
for path in Path("src").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:
                missing.append(f"{path}:{node.lineno}:{node.name}")

print(f"missing_docstrings {len(missing)}")
for item in missing:
    print(item)
