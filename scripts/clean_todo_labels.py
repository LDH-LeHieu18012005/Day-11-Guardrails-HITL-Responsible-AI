"""Rename completed TODO labels to Task labels in Python source files."""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


for path in (ROOT / "src").rglob("*.py"):
    text = path.read_text(encoding="utf-8")
    updated = text.replace("TODO", "Task")
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}")
