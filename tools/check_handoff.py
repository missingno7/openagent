#!/usr/bin/env python3
"""Run the standard clean-handoff checks for OpenAgent.

Unlike ``python -m compileall``, this script uses AST parsing and in-process
``runpy`` execution with ``PYTHONDONTWRITEBYTECODE=1`` so it can validate the
tree without leaving ``__pycache__`` directories behind.  It also removes any
stale bytecode before and after the checks so ``tools/audit_project.py`` stays
meaningful.
"""
from __future__ import annotations

import ast
import os
import shutil
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIRS = (ROOT / "openagent", ROOT / "tools")
AUDIT_TESTS = (
    "tools/audit_mechanics_status.py",
    "tools/audit_tick_accuracy.py",
    "tools/audit_project.py",
)

SMOKE_TESTS = (
    "tools/check_render_interpolation.py",
    "tools/check_overworld_collision.py",
    "tools/check_death_reset.py",
    "tools/check_death_camera_platform.py",
    "tools/check_runtime_hard_death_import.py",
    "tools/check_landmine_no_extra_explosions.py",
    "tools/check_state2b_decorative.py",
    "tools/check_barrel_vertical_fall.py",
    "tools/check_barrel_player_interaction.py",
    "tools/check_stationary_shooter_accuracy.py",
    "tools/check_state23_contact_bomb_accuracy.py",
    "tools/check_player_motion_accuracy.py",
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def remove_pycache() -> int:
    removed = 0
    for cache_dir in ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            removed += 1
    for pyc in ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
        removed += 1
    return removed


def parse_python_sources() -> None:
    errors: list[str] = []
    for directory in PYTHON_DIRS:
        for py_file in sorted(directory.rglob("*.py")):
            try:
                ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            except SyntaxError as exc:
                errors.append(f"{rel(py_file)}:{exc.lineno}: {exc.msg}")
    if errors:
        raise SystemExit("Python parse failed:\n" + "\n".join(f" - {err}" for err in errors))


def run_script(script: str) -> None:
    """Run a small project check in-process without leaving bytecode behind.

    Running the checks in subprocesses is conceptually cleaner, but some host
    environments can stall after a long chain of short Python child processes.
    These handoff checks are intentionally pure scripts, so executing them via
    ``runpy`` keeps the guard reliable while still preserving each script's
    normal ``if __name__ == "__main__"`` path and exit code.
    """
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    print(f"$ {sys.executable} {script}", flush=True)
    old_argv = sys.argv[:]
    sys.argv = [script]
    try:
        runpy.run_path(str(ROOT / script), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code not in (0, None):
            raise
    finally:
        sys.argv = old_argv


def main() -> int:
    removed_before = remove_pycache()
    if removed_before:
        print(f"Removed {removed_before} stale bytecode/cache entr{'y' if removed_before == 1 else 'ies'} before checks.", flush=True)

    parse_python_sources()
    print("Python source parse OK", flush=True)

    for script in AUDIT_TESTS:
        run_script(script)

    for script in SMOKE_TESTS:
        run_script(script)

    removed_after = remove_pycache()
    if removed_after:
        print(f"Removed {removed_after} bytecode/cache entr{'y' if removed_after == 1 else 'ies'} after checks.", flush=True)

    print("Handoff checks OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
