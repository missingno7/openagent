#!/usr/bin/env python3
"""Inspect Secret Agent data files against OpenCrystalCaves assumptions.

The goal is to keep early reverse-engineering facts reproducible.  This does
not try to emulate the game yet; it reports which files already match known
Crystal Caves-era formats and which still need code reconstruction.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SND_RECORD_SIZE = 610
PCX_EGA16 = [
    (0x00, 0x00, 0x00),
    (0x00, 0x00, 0xAA),
    (0x00, 0xAA, 0x00),
    (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00),
    (0xAA, 0x00, 0xAA),
    (0xAA, 0x55, 0x00),
    (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55),
    (0x55, 0x55, 0xFF),
    (0x55, 0xFF, 0x55),
    (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55),
    (0xFF, 0x55, 0xFF),
    (0xFF, 0xFF, 0x55),
    (0xFF, 0xFF, 0xFF),
]


@dataclass(frozen=True)
class PcxInfo:
    path: Path
    version: int
    bits_per_pixel: int
    width: int
    height: int
    planes: int
    bytes_per_line: int


def iter_files(root: Path, pattern: str) -> Iterable[Path]:
    return sorted(root.glob(pattern), key=lambda p: p.name.lower())


def pcx_info(path: Path) -> PcxInfo | None:
    data = path.read_bytes()
    if len(data) < 128 or data[0] != 0x0A:
        return None
    xmin, ymin, xmax, ymax = struct.unpack_from("<HHHH", data, 4)
    planes = data[65]
    bytes_per_line = struct.unpack_from("<H", data, 66)[0]
    return PcxInfo(
        path=path,
        version=data[1],
        bits_per_pixel=data[3],
        width=xmax - xmin + 1,
        height=ymax - ymin + 1,
        planes=planes,
        bytes_per_line=bytes_per_line,
    )


def decode_pcx(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    info = pcx_info(path)
    if info is None:
        raise ValueError(f"{path} is not a PCX file")
    raw = path.read_bytes()
    pos = 128
    decoded = bytearray()
    target = info.height * info.planes * info.bytes_per_line
    while pos < len(raw) and len(decoded) < target:
        value = raw[pos]
        pos += 1
        if value & 0xC0 == 0xC0:
            if pos >= len(raw):
                break
            count = value & 0x3F
            decoded.extend([raw[pos]] * count)
            pos += 1
        else:
            decoded.append(value)
    if len(decoded) < target:
        raise ValueError(f"{path} ended before the PCX image data was complete")

    palette = []
    for i in range(16):
        r, g, b = raw[16 + i * 3 : 19 + i * 3]
        palette.append((r, g, b))
    if all(c == (0, 0, 0) for c in palette[1:]):
        palette = PCX_EGA16

    pixels: list[tuple[int, int, int]] = []
    row_stride = info.planes * info.bytes_per_line
    for y in range(info.height):
        row = decoded[y * row_stride : (y + 1) * row_stride]
        for x in range(info.width):
            bit = 7 - (x & 7)
            byte_index = x >> 3
            color_index = 0
            for plane in range(info.planes):
                plane_byte = row[plane * info.bytes_per_line + byte_index]
                color_index |= ((plane_byte >> bit) & 1) << plane
            pixels.append(palette[color_index & 0x0F])
    return info.width, info.height, pixels


def write_ppm(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        for r, g, b in pixels:
            f.write(bytes((r, g, b)))


def prographx_chunks(path: Path) -> tuple[bool, list[tuple[int, int, int, int, int]]]:
    data = path.read_bytes()
    offset = 0
    chunks: list[tuple[int, int, int, int, int]] = []
    while offset + 3 <= len(data):
        count, width, height = data[offset], data[offset + 1], data[offset + 2]
        size = count * width * height * 5
        chunks.append((offset, count, width, height, size))
        offset += 3 + size
        if count != 50:
            return False, chunks
        if offset == len(data):
            return True, chunks
        if offset > len(data):
            return False, chunks
    return offset == len(data), chunks


def sound_summary(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    first_values = []
    plausible_prefix = 0
    if len(data) >= SND_RECORD_SIZE:
        values = struct.unpack_from("<20h", data, 0)
        first_values = list(values)
        for value in values:
            if value == -1 or 0 <= value <= 20000:
                plausible_prefix += 1
    return {
        "size": len(data),
        "record_count_if_cc_sound": len(data) / SND_RECORD_SIZE,
        "first_20_signed_words": first_values,
        "plausible_prefix_words": plausible_prefix,
    }


def selected_strings(disassembly_dir: Path, episode: int) -> list[str]:
    path = disassembly_dir / f"SAM{episode}_strings.txt"
    if not path.exists():
        return []
    asset_pattern = re.compile(r"\bSAM[0-9A-Z-]*\.(?:GFX|SND|APO|TTL|CRD|END|CFG)U?\b", re.IGNORECASE)
    hits = []
    for line in path.read_text(errors="replace").splitlines():
        if asset_pattern.search(line) or "Decompressing Graphics" in line:
            hits.append(line.strip())
    return hits


def build_report(root: Path) -> str:
    game_data = root / "game_data"
    disassembly = root / "dissassembly"
    lines: list[str] = []
    lines.append("# Secret Agent Asset Inventory")
    lines.append("")
    lines.append("Generated by `tools/inspect_secret_agent_assets.py`.")
    lines.append("")

    metadata_path = disassembly / "metadata.json"
    if metadata_path.exists():
        lines.append("## EXE Metadata")
        meta = json.loads(metadata_path.read_text())
        lines.append("")
        lines.append("| Episode | Packed | Unpacked | Entry | Relocs | Load module |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for item in meta:
            episode = item["file"].split("_", 1)[0]
            lines.append(
                f"| {episode} | {item['packed_size']} | {item['size']} | "
                f"0x{item['entry_linear_offset']:04X} | {item['relocation_count']} | "
                f"{item['load_module_size']} |"
            )
        lines.append("")

    lines.append("## Images")
    lines.append("")
    lines.append("| File | Size | PCX | Geometry | Planes | Bytes/line |")
    lines.append("|---|---:|---|---:|---:|---:|")
    for path in iter_files(game_data, "SAM*.*"):
        if path.suffix.upper() not in {".APO", ".TTL", ".CRD", ".END"}:
            continue
        info = pcx_info(path)
        if info:
            lines.append(
                f"| {path.name} | {path.stat().st_size} | yes | "
                f"{info.width}x{info.height} | {info.planes} | {info.bytes_per_line} |"
            )
        else:
            lines.append(f"| {path.name} | {path.stat().st_size} | no |  |  |  |")
    lines.append("")

    lines.append("## Graphics Chunks")
    lines.append("")
    lines.append("| File | Size | OCC ProGraphx from byte 0 | First interpreted chunk |")
    lines.append("|---|---:|---|---|")
    for path in iter_files(game_data, "*.GFX"):
        ok, chunks = prographx_chunks(path)
        first = chunks[0] if chunks else None
        first_text = ""
        if first:
            first_text = f"offset={first[0]}, count={first[1]}, w={first[2]}, h={first[3]}, bytes={first[4]}"
        lines.append(f"| {path.name} | {path.stat().st_size} | {'yes' if ok else 'no'} | {first_text} |")
    lines.append("")

    lines.append("## Sounds")
    lines.append("")
    lines.append("| File | Size | Records if CC layout | Plausible first 20 words | First 8 signed words |")
    lines.append("|---|---:|---:|---:|---|")
    for path in iter_files(game_data, "*.SND"):
        summary = sound_summary(path)
        first8 = ", ".join(str(v) for v in summary["first_20_signed_words"][:8])
        lines.append(
            f"| {path.name} | {summary['size']} | "
            f"{summary['record_count_if_cc_sound']:.1f} | {summary['plausible_prefix_words']} | "
            f"`{first8}` |"
        )
    lines.append("")

    lines.append("## Filename Strings In EXEs")
    for episode in (1, 2, 3):
        hits = selected_strings(disassembly, episode)
        lines.append("")
        lines.append(f"### SAM{episode}")
        lines.append("")
        for hit in hits:
            lines.append(f"- `{hit}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--markdown", type=Path, help="Write a markdown inventory report.")
    parser.add_argument("--extract-pcx", type=Path, help="Write PCX previews as binary PPM files.")
    args = parser.parse_args()

    root = args.root
    if args.extract_pcx:
        for path in iter_files(root / "game_data", "SAM*.*"):
            if path.suffix.upper() not in {".APO", ".TTL", ".CRD", ".END"}:
                continue
            width, height, pixels = decode_pcx(path)
            preview_name = f"{path.stem}_{path.suffix[1:].lower()}.ppm"
            write_ppm(args.extract_pcx / preview_name, width, height, pixels)

    report = build_report(root)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report + "\n", encoding="utf-8")
    elif not args.extract_pcx:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
