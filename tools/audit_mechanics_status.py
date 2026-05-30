#!/usr/bin/env python3
"""Validate the reverse-engineering mechanics status registry.

This is not a gameplay test.  It is a handoff/readability guard: it makes sure
that each known mechanic declares whether it is ASM-verified, partial,
heuristic, known-wrong, or unimplemented.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'docs' / 'registry' / 'mechanics_status.json'
VALID_STATUSES = {
    'asm_verified',
    'asm_partial',
    'data_verified',
    'heuristic',
    'known_wrong',
    'unimplemented',
}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace('\\', '/')


def main() -> int:
    problems: list[str] = []
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    entries = data.get('entries', [])
    seen_ids: set[str] = set()

    if not entries:
        problems.append('No mechanics entries found.')

    for i, entry in enumerate(entries):
        prefix = f'entry #{i}'
        ident = entry.get('id')
        if not ident:
            problems.append(f'{prefix}: missing id')
            continue
        prefix = ident
        if ident in seen_ids:
            problems.append(f'{prefix}: duplicate id')
        seen_ids.add(ident)

        status = entry.get('status')
        if status not in VALID_STATUSES:
            problems.append(f'{prefix}: invalid status {status!r}')

        if not entry.get('title'):
            problems.append(f'{prefix}: missing title')
        if not entry.get('area'):
            problems.append(f'{prefix}: missing area')
        if not entry.get('implemented_in'):
            problems.append(f'{prefix}: missing implemented_in')
        if status != 'unimplemented' and not entry.get('evidence'):
            problems.append(f'{prefix}: implemented/partial mechanic needs evidence')
        if status in {'asm_partial', 'heuristic', 'known_wrong', 'unimplemented'} and not entry.get('next_actions'):
            problems.append(f'{prefix}: non-final mechanic needs next_actions')
        if status in {'heuristic', 'known_wrong'} and not entry.get('known_gaps'):
            problems.append(f'{prefix}: suspect mechanic should state known_gaps')

        for impl in entry.get('implemented_in', []):
            # Some entries point to a broad module that may exist after refactors; require current paths to exist.
            path = ROOT / impl
            if not path.exists():
                problems.append(f'{prefix}: implemented_in path does not exist: {impl}')

    if problems:
        print('Mechanics status audit failed:')
        for problem in problems:
            print(' - ' + problem)
        return 1

    print(f'Mechanics status audit OK: {len(entries)} entries, {len(seen_ids)} unique ids.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
