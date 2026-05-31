#!/usr/bin/env python3
"""Validate the tick-accuracy ledger.

The ledger is the bridge between scattered pass notes, ASM references and the
Python runtime.  This audit intentionally stays lightweight: it catches stale
paths, unknown mechanics, duplicate phase IDs and missing next actions before a
handoff zip is made.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'docs' / 'registry' / 'tick_accuracy_ledger.json'
MECHANICS = ROOT / 'docs' / 'registry' / 'mechanics_status.json'
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


def path_part(entrypoint: str) -> str:
    return entrypoint.split('::', 1)[0]


def main() -> int:
    problems: list[str] = []
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    mechanics = json.loads(MECHANICS.read_text(encoding='utf-8'))
    known_mechanics = {entry['id'] for entry in mechanics.get('entries', []) if entry.get('id')}
    phases = ledger.get('phases', [])
    seen: set[str] = set()

    if ledger.get('schema_version') != 1:
        problems.append('schema_version must be 1')
    if not phases:
        problems.append('no phases found')

    for index, phase in enumerate(phases):
        ident = phase.get('id')
        prefix = ident or f'phase #{index}'
        if not ident:
            problems.append(f'{prefix}: missing id')
            continue
        if ident in seen:
            problems.append(f'{prefix}: duplicate id')
        seen.add(ident)

        if phase.get('status') not in VALID_STATUSES:
            problems.append(f'{prefix}: invalid status {phase.get("status")!r}')
        if not phase.get('title'):
            problems.append(f'{prefix}: missing title')
        if not phase.get('runtime_entrypoints'):
            problems.append(f'{prefix}: missing runtime_entrypoints')
        if not phase.get('asm_refs'):
            problems.append(f'{prefix}: missing asm_refs')
        if not phase.get('exact_claims'):
            problems.append(f'{prefix}: missing exact_claims')
        if phase.get('status') in {'asm_partial', 'heuristic', 'known_wrong', 'unimplemented'}:
            if not phase.get('blind_spots'):
                problems.append(f'{prefix}: non-final phase needs blind_spots')
            if not phase.get('next_actions'):
                problems.append(f'{prefix}: non-final phase needs next_actions')

        for mechanic_id in phase.get('registry_ids', []):
            if mechanic_id not in known_mechanics:
                problems.append(f'{prefix}: unknown registry id {mechanic_id!r}')
        for entrypoint in phase.get('runtime_entrypoints', []):
            path = ROOT / path_part(entrypoint)
            if not path.exists():
                problems.append(f'{prefix}: runtime entrypoint path does not exist: {entrypoint}')
        for doc in phase.get('evidence_docs', []):
            path = ROOT / doc
            if not path.exists():
                problems.append(f'{prefix}: evidence doc does not exist: {doc}')
        for test in phase.get('tests', []):
            path = ROOT / test
            if not path.exists():
                problems.append(f'{prefix}: test path does not exist: {test}')

    if problems:
        print('Tick accuracy ledger audit failed:')
        for problem in problems:
            print(' - ' + problem)
        return 1

    print(f'Tick accuracy ledger audit OK: {len(phases)} phases, {len(seen)} unique ids.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
