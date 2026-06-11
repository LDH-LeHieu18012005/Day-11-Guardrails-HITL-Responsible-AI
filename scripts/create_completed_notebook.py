"""Create a completed submission notebook with executed outputs."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
NOTEBOOK = ROOT / "notebooks" / "lab11_guardrails_hitl.ipynb"
COPY = ROOT / "notebooks" / "assignment11_completed.ipynb"


def run_command(args: list[str], cwd: Path) -> str:
    """Run a command and return combined stdout/stderr for notebook output."""
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    return completed.stdout


def code_cell(source: str, output: str = "") -> dict:
    """Build a code cell with optional captured stdout."""
    outputs = []
    if output:
        outputs.append({
            "name": "stdout",
            "output_type": "stream",
            "text": output.splitlines(keepends=True),
        })
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": outputs,
        "source": source.splitlines(keepends=True),
    }


def markdown_cell(source: str) -> dict:
    """Build a markdown cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def main() -> None:
    """Generate the completed notebook and a submission copy."""
    production_output = run_command([sys.executable, "production_pipeline.py"], SRC)
    comparison_output = run_command([sys.executable, "main.py", "--part", "3"], SRC)
    guardrails_output = run_command([sys.executable, "main.py", "--part", "2"], SRC)
    hitl_output = run_command([sys.executable, "main.py", "--part", "4"], SRC)
    report_text = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    audit_path = ROOT / "artifacts" / "security_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_summary = {
        "events": len(audit),
        "passed": sum(1 for item in audit if item.get("passed")),
        "blocked": sum(1 for item in audit if not item.get("passed")),
        "blocked_by": {},
    }
    for item in audit:
        layer = item.get("blocked_by") or "none"
        audit_summary["blocked_by"][layer] = audit_summary["blocked_by"].get(layer, 0) + 1

    notebook = {
        "cells": [
            markdown_cell(
                "# Assignment 11 - Completed Defense-in-Depth Pipeline\n\n"
                "This notebook is the completed submission version. It uses the implemented Python modules in `src/`, runs the full production defense pipeline, shows before/after security comparison, prints guardrail tests, and includes the individual report summary.\n\n"
                "Environment note: Google ADK / NeMo can run when their dependencies and `GOOGLE_API_KEY` are available. This repository also includes deterministic local fallbacks so the notebook runs end-to-end offline."
            ),
            markdown_cell(
                "## What Was Implemented\n\n"
                "- 5 adversarial prompt families and AI-red-team fallback generation\n"
                "- Input guardrails: injection detection, Vietnamese/English patterns, topic filter, ADK-compatible plugin\n"
                "- Output guardrails: PII/secrets redaction, local plus optional LLM-as-Judge, ADK-compatible plugin\n"
                "- NeMo Colang rules for basic injection, role confusion, encoding extraction, Vietnamese injection, and off-topic handling\n"
                "- Before/after attack comparison and automated security testing pipeline\n"
                "- HITL confidence router and 3 banking decision points\n"
                "- Production pipeline with rate limiting, audit logging, monitoring alerts, and required test suites"
            ),
            code_cell(
                "import sys\n"
                "from pathlib import Path\n\n"
                "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
                "SRC = ROOT / 'src'\n"
                "sys.path.insert(0, str(SRC))\n\n"
                "print('ROOT:', ROOT)\n"
                "print('SRC:', SRC)\n",
                f"ROOT: {ROOT}\nSRC: {SRC}\n",
            ),
            markdown_cell("## Required Production Pipeline Tests"),
            code_cell(
                "import subprocess, sys\n"
                "result = subprocess.run(\n"
                "    [sys.executable, 'production_pipeline.py'],\n"
                "    cwd=str(SRC), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120\n"
                ")\n"
                "print(result.stdout)\n",
                production_output,
            ),
            markdown_cell("## Before / After Security Comparison"),
            code_cell(
                "result = subprocess.run(\n"
                "    [sys.executable, 'main.py', '--part', '3'],\n"
                "    cwd=str(SRC), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120\n"
                ")\n"
                "print(result.stdout)\n",
                comparison_output,
            ),
            markdown_cell("## Guardrail Component Tests"),
            code_cell(
                "result = subprocess.run(\n"
                "    [sys.executable, 'main.py', '--part', '2'],\n"
                "    cwd=str(SRC), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120\n"
                ")\n"
                "print(result.stdout)\n",
                guardrails_output,
            ),
            markdown_cell("## HITL Router and Decision Points"),
            code_cell(
                "result = subprocess.run(\n"
                "    [sys.executable, 'main.py', '--part', '4'],\n"
                "    cwd=str(SRC), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120\n"
                ")\n"
                "print(result.stdout)\n",
                hitl_output,
            ),
            markdown_cell("## Audit Log Summary"),
            code_cell(
                "import json\n"
                "audit_path = ROOT / 'artifacts' / 'security_audit.json'\n"
                "audit = json.loads(audit_path.read_text(encoding='utf-8'))\n"
                "summary = {\n"
                "    'events': len(audit),\n"
                "    'passed': sum(1 for item in audit if item.get('passed')),\n"
                "    'blocked': sum(1 for item in audit if not item.get('passed')),\n"
                "    'blocked_by': {},\n"
                "}\n"
                "for item in audit:\n"
                "    layer = item.get('blocked_by') or 'none'\n"
                "    summary['blocked_by'][layer] = summary['blocked_by'].get(layer, 0) + 1\n"
                "print(json.dumps(summary, indent=2))\n",
                json.dumps(audit_summary, indent=2) + "\n",
            ),
            markdown_cell("## Individual Report"),
            markdown_cell(report_text),
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    NOTEBOOK.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    COPY.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {NOTEBOOK}")
    print(f"Wrote {COPY}")


if __name__ == "__main__":
    main()
