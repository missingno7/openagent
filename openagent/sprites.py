from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .loader import ensure_editor_importable

ROOT = Path(__file__).resolve().parents[1]
ensure_editor_importable(ROOT)

from secret_agent_editor.constants import EGA_PALETTE
from secret_agent_editor.crypto import decrypt_secret_agent


@dataclass
class Tileset8:
    banks: list[list[Image.Image]]

    def get(self, bank: int, tile: int) -> Image.Image | None:
        if 0 <= bank < len(self.banks) and 0 <= tile < len(self.banks[bank]):
            return self.banks[bank][tile]
        return None


def decode_prographx_8x8(encrypted: bytes) -> Tileset8:
    """Decode SAM?02.GFX into 8x8 masked EGA sprites.

    Camoto identifies this as ``tls-sagent-2k`` with the
    ``xor-sagent-8sprite`` filter.  It is the Secret Agent wrapper around the
    Crystal Caves tileset handler, so every 2048-byte encrypted block decrypts
    to a headered sub-tileset: [num_tiles, width_bytes, height], followed by
    masked EGA byte-planar sprite data and padding.
    """
    plain = decrypt_secret_agent(encrypted, row_key_reset=2048)
    bank_size = 2048
    banks: list[list[Image.Image]] = []
    for bank_start in range(0, len(plain), bank_size):
        chunk = plain[bank_start:bank_start + bank_size]
        if len(chunk) < 3:
            continue
        num_tiles, width_bytes, height = chunk[0], chunk[1], chunk[2]
        if width_bytes <= 0 or height <= 0:
            continue
        sprite_size = width_bytes * height * 5
        data_start = 3
        if len(chunk) < data_start + num_tiles * sprite_size:
            continue
        sprites: list[Image.Image] = []
        for i in range(num_tiles):
            off = data_start + i * sprite_size
            if width_bytes == 1 and height == 8:
                sprites.append(_decode_masked_ega_sprite_8(chunk[off:off + sprite_size]))
            else:
                sprites.append(_decode_masked_ega_sprite_generic(chunk[off:off + sprite_size], width_bytes * 8, height, width_bytes))
        banks.append(sprites)
    return Tileset8(banks)


def _decode_masked_ega_sprite_generic(buf: bytes, width: int, height: int, width_bytes: int) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = img.load()
    i = 0
    for y in range(height):
        for xb in range(width_bytes):
            if i + 5 > len(buf):
                return img
            opaque, blue, green, red, inten = buf[i:i + 5]
            i += 5
            for bit in range(8):
                mask = 0x80 >> bit
                if not (opaque & mask):
                    continue
                color = 0
                if blue & mask:
                    color |= 1
                if green & mask:
                    color |= 2
                if red & mask:
                    color |= 4
                if inten & mask:
                    color |= 8
                px[xb * 8 + bit, y] = (*EGA_PALETTE[color], 255)
    return img

def _decode_masked_ega_sprite_8(buf: bytes) -> Image.Image:
    img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    px = img.load()
    i = 0
    for y in range(8):
        if i + 5 > len(buf):
            return img
        opaque, blue, green, red, inten = buf[i:i + 5]
        i += 5
        for bit in range(8):
            mask = 0x80 >> bit
            if not (opaque & mask):
                continue
            color = 0
            if blue & mask:
                color |= 1
            if green & mask:
                color |= 2
            if red & mask:
                color |= 4
            if inten & mask:
                color |= 8
            px[bit, y] = (*EGA_PALETTE[color], 255)
    return img


def render_tileset8_atlas(tileset: Tileset8, *, scale: int = 2) -> Image.Image:
    cols = 25
    rows_per_bank = 2
    cell = 12
    width = cols * cell
    height = len(tileset.banks) * rows_per_bank * cell
    atlas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    for bank, sprites in enumerate(tileset.banks):
        bank_y = bank * rows_per_bank * cell
        for idx, sprite in enumerate(sprites):
            x = (idx % cols) * cell + 2
            y = bank_y + (idx // cols) * cell + 2
            atlas.alpha_composite(sprite, (x, y))
    if scale != 1:
        atlas = atlas.resize((atlas.width * scale, atlas.height * scale), Image.Resampling.NEAREST)
    return atlas
