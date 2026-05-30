from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PIL import Image

from .constants import EGA_PALETTE
from .crypto import decrypt_secret_agent


@dataclass
class Tileset16:
    banks: List[List[Image.Image]]

    def get(self, bank: int, tile: int) -> Optional[Image.Image]:
        if 0 <= bank < len(self.banks) and 0 <= tile < len(self.banks[bank]):
            return self.banks[bank][tile]
        return None


@dataclass
class Tileset8:
    banks: List[List[Image.Image]]

    def get(self, bank: int, tile: int) -> Optional[Image.Image]:
        if 0 <= bank < len(self.banks) and 0 <= tile < len(self.banks[bank]):
            return self.banks[bank][tile]
        return None


def decode_prographx_8x8(encrypted: bytes) -> Tileset8:
    """Decode SAM?02.GFX into 8x8 masked EGA UI/font cells.

    This follows Camoto's Secret Agent definition exactly: ``SAM?02.GFX`` is
    ``tls-sagent-2k`` with the ``xor-sagent-8sprite`` filter.  The encrypted
    key resets every 2048 bytes.  After decryption each 2048-byte block is a
    Crystal-Caves-style sub-tileset:

      byte 0: number of sprites (normally 50)
      byte 1: width in byte-cells (1 => 8 pixels)
      byte 2: height (8 pixels)
      bytes 3..2002: 50 * 40-byte masked EGA sprites
      bytes 2003..2047: padding

    Pass 59 incorrectly removed the three-byte header and shifted all HUD
    glyphs/icons by three bytes, which made the icons look like CGA/noise.
    """
    plain = decrypt_secret_agent(encrypted, row_key_reset=2048)
    banks: List[List[Image.Image]] = []
    bank_size = 2048
    for bank_start in range(0, len(plain), bank_size):
        chunk = plain[bank_start:bank_start + bank_size]
        if len(chunk) < 3:
            continue
        num_tiles, width_bytes, height = chunk[0], chunk[1], chunk[2]
        if width_bytes <= 0 or height <= 0:
            continue
        cell_size = width_bytes * height * 5
        data_start = 3
        if len(chunk) < data_start + num_tiles * cell_size:
            continue
        cells: List[Image.Image] = []
        for t in range(num_tiles):
            off = data_start + t * cell_size
            if width_bytes == 1 and height == 8:
                cells.append(_decode_masked_ega_tile_8(chunk[off:off + cell_size]))
            else:
                cells.append(_decode_masked_ega_tile_generic(chunk[off:off + cell_size], width_bytes * 8, height, width_bytes))
        banks.append(cells)
    return Tileset8(banks)


def _decode_masked_ega_tile_generic(buf: bytes, width: int, height: int, width_bytes: int) -> Image.Image:
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

def _decode_masked_ega_tile_8(buf: bytes) -> Image.Image:
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


def decode_prographx_16x16(encrypted: bytes) -> Tileset16:
    """Decode SAM?01.GFX into 16 banks x 50 masked 16x16 EGA tiles.

    Camoto identifies this as ``tls-sagent-8k``.  Each 8064-byte bank has a
    3-byte ProGraphx header followed by 50 tiles.  A tile is 16 rows * 2 byte
    cells * 5 planes = 160 bytes.  The planes are interleaved by row/cell:
    opaque mask, blue, green, red, intensity.
    """
    plain = decrypt_secret_agent(encrypted, row_key_reset=8064)
    banks: List[List[Image.Image]] = []
    bank_size = 8064
    tile_size = 160
    data_start = 3
    for bank_start in range(0, len(plain) - tile_size + 1, bank_size):
        chunk = plain[bank_start:bank_start + bank_size]
        if len(chunk) < data_start + 50 * tile_size:
            continue
        tiles: List[Image.Image] = []
        for t in range(50):
            off = data_start + t * tile_size
            tiles.append(_decode_masked_ega_tile_16(chunk[off:off + tile_size]))
        banks.append(tiles)
    return Tileset16(banks)


def _decode_masked_ega_tile_16(buf: bytes) -> Image.Image:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    i = 0
    for y in range(16):
        for xb in range(2):
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
