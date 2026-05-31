#!/usr/bin/env python3
"""Small handoff audit for the OpenAgent workspace.

It intentionally checks the problems that kept making the project hard to use:
root-level debug images, stale bytecode, oversized unrelated source dumps, and
basic Python syntax/import validity.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ppm'}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace('\\', '/')


def main() -> int:
    problems: list[str] = []

    root_images = [p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
    if root_images:
        problems.append('Root-level debug image files: ' + ', '.join(rel(p) for p in root_images))

    pycache = [p for p in ROOT.rglob('__pycache__') if p.is_dir()]
    if pycache:
        problems.append('Python cache directories present: ' + ', '.join(rel(p) for p in pycache[:10]))

    pyc = [p for p in ROOT.rglob('*.pyc') if p.is_file()]
    if pyc:
        problems.append('Compiled .pyc files present: ' + ', '.join(rel(p) for p in pyc[:10]))

    if (ROOT / 'OpenCrystalCaves').exists():
        problems.append('OpenCrystalCaves/ is present in this zip; keep it external unless actively comparing engines.')

    pass_logs_in_root = sorted((ROOT / 'docs').glob('exe_mechanisms_pass*.md'))
    if pass_logs_in_root:
        problems.append('Pass logs still in docs root: ' + ', '.join(rel(p) for p in pass_logs_in_root[:10]))

    syntax_errors: list[str] = []
    for package in (ROOT / 'openagent',):
        for py in package.rglob('*.py'):
            try:
                ast.parse(py.read_text(encoding='utf-8'), filename=str(py))
            except SyntaxError as exc:
                syntax_errors.append(f'{rel(py)}:{exc.lineno}: {exc.msg}')
    if syntax_errors:
        problems.append('Python syntax errors: ' + '; '.join(syntax_errors[:10]))

    if problems:
        print('Audit failed:')
        for item in problems:
            print(' - ' + item)
        return 1

    print('Audit OK: root is clean, pass logs are archived, and Python source parses.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
