"""Convert BMPs to the strict BMP3 format MakeNSIS accepts.

NSIS only understands "old" BMPs: a 40-byte BITMAPINFOHEADER, uncompressed
(BI_RGB), bottom-up, with up to 24 bits per pixel. Modern tools (Figma,
Photoshop, ImageMagick defaults) tend to emit a BITMAPV5HEADER with
BI_BITFIELDS at 32bpp, which triggers `warning 5040: Unsupported format`
and falls back to the default branding bitmaps.

This script reads every BMP passed on the command line (or, by default,
`src-tauri/installer/nsis-header.bmp` and `nsis-sidebar.bmp`), decodes
the pixels using only the standard library, and rewrites the file in
place as a 24bpp BMP3. The output is byte-for-byte what NSIS expects.

Usage:
    python scripts/convert-nsis-bmps.py
    python scripts/convert-nsis-bmps.py path/to/one.bmp path/to/two.bmp
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = [
    REPO_ROOT / "src-tauri" / "installer" / "nsis-header.bmp",
    REPO_ROOT / "src-tauri" / "installer" / "nsis-sidebar.bmp",
]


def _mask_shift(mask: int) -> tuple[int, int]:
    """Return (shift, bits) so that `(pixel & mask) >> shift` is the channel."""
    if mask == 0:
        return 0, 0
    shift = 0
    m = mask
    while m & 1 == 0:
        m >>= 1
        shift += 1
    bits = 0
    while m:
        m >>= 1
        bits += 1
    return shift, bits


def _scale_to_8(value: int, bits: int) -> int:
    if bits == 0:
        return 0
    if bits == 8:
        return value & 0xFF
    if bits > 8:
        return (value >> (bits - 8)) & 0xFF
    max_in = (1 << bits) - 1
    return (value * 255 + max_in // 2) // max_in


def _decode_rows(data: bytes, width: int, height: int, dib: dict) -> list[bytes]:
    """Return a list of BGR rows, top-to-bottom, regardless of source layout."""
    bpp = dib["bpp"]
    comp = dib["compression"]
    top_down = height < 0
    h = abs(height)

    if bpp == 24 and comp == 0:
        stride = ((width * 3 + 3) // 4) * 4
        rows = [data[i * stride : i * stride + width * 3] for i in range(h)]
    elif bpp == 32 and comp in (0, 3):
        if comp == 3:
            r_mask = dib["red_mask"]
            g_mask = dib["green_mask"]
            b_mask = dib["blue_mask"]
        else:
            r_mask, g_mask, b_mask = 0x00FF0000, 0x0000FF00, 0x000000FF
        r_shift, r_bits = _mask_shift(r_mask)
        g_shift, g_bits = _mask_shift(g_mask)
        b_shift, b_bits = _mask_shift(b_mask)
        stride = width * 4
        rows = []
        for y in range(h):
            row_in = data[y * stride : (y + 1) * stride]
            out = bytearray(width * 3)
            for x in range(width):
                pixel = int.from_bytes(row_in[x * 4 : x * 4 + 4], "little")
                r = _scale_to_8((pixel & r_mask) >> r_shift, r_bits)
                g = _scale_to_8((pixel & g_mask) >> g_shift, g_bits)
                b = _scale_to_8((pixel & b_mask) >> b_shift, b_bits)
                out[x * 3 + 0] = b
                out[x * 3 + 1] = g
                out[x * 3 + 2] = r
            rows.append(bytes(out))
    else:
        raise ValueError(
            f"Unsupported source BMP: bpp={bpp} compression={comp}. "
            "Re-export as 24- or 32-bit BMP."
        )

    if not top_down:
        rows.reverse()
    return rows


def _parse_bmp(path: Path) -> tuple[int, int, list[bytes]]:
    raw = path.read_bytes()
    if raw[:2] != b"BM":
        raise ValueError(f"{path}: not a BMP file")

    pix_offset = struct.unpack_from("<I", raw, 10)[0]
    dib_size = struct.unpack_from("<I", raw, 14)[0]
    width = struct.unpack_from("<i", raw, 18)[0]
    height = struct.unpack_from("<i", raw, 22)[0]
    bpp = struct.unpack_from("<H", raw, 28)[0]
    compression = struct.unpack_from("<I", raw, 30)[0]

    red_mask = green_mask = blue_mask = 0
    if dib_size >= 56:
        red_mask, green_mask, blue_mask = struct.unpack_from("<III", raw, 54)
    elif compression == 3:
        red_mask, green_mask, blue_mask = struct.unpack_from(
            "<III", raw, 14 + dib_size
        )

    dib = {
        "bpp": bpp,
        "compression": compression,
        "red_mask": red_mask,
        "green_mask": green_mask,
        "blue_mask": blue_mask,
    }

    rows = _decode_rows(raw[pix_offset:], width, height, dib)
    return width, abs(height), rows


def _encode_bmp3(width: int, height: int, rows_top_down: list[bytes]) -> bytes:
    stride = ((width * 3 + 3) // 4) * 4
    pad = b"\x00" * (stride - width * 3)
    pixel_bytes = bytearray()
    for row in reversed(rows_top_down):
        pixel_bytes.extend(row)
        pixel_bytes.extend(pad)

    file_size = 14 + 40 + len(pixel_bytes)
    header = struct.pack(
        "<2sIHHI",
        b"BM",
        file_size,
        0,
        0,
        14 + 40,
    )
    dib = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        24,
        0,
        len(pixel_bytes),
        2835,
        2835,
        0,
        0,
    )
    return header + dib + bytes(pixel_bytes)


def convert(path: Path) -> None:
    width, height, rows = _parse_bmp(path)
    out = _encode_bmp3(width, height, rows)
    path.write_bytes(out)
    print(f"  rewrote {path} as {width}x{height} 24-bit BMP3 ({len(out)} bytes)")


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or DEFAULT_TARGETS
    print("Converting BMPs to NSIS-compatible BMP3:")
    for target in targets:
        if not target.exists():
            print(f"  skip (missing): {target}")
            continue
        try:
            convert(target)
        except Exception as exc:
            print(f"  FAILED {target}: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
